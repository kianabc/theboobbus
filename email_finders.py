"""Email finder integrations: Hunter.io and Apollo.io"""

import os
import logging
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

HR_TITLES = [
    # HR
    "human resources",
    "hr director",
    "hr manager",
    "head of hr",
    "vp of hr",
    "chief people officer",
    "people operations",
    "head of people",
    "talent acquisition",
    "recruiting manager",
    "director of recruiting",
    "head of talent",
    # Benefits & Wellness — key decision makers for Boob Bus
    "benefits manager",
    "benefits director",
    "benefits coordinator",
    "benefits specialist",
    "wellness manager",
    "wellness director",
    "wellness coordinator",
    "health and wellness",
    "employee wellness",
    "employee health",
    "employee experience",
    "employee engagement",
    # Office / Admin — at smaller companies
    "office manager",
    "office administrator",
    "workplace experience",
]


def _domain_from_url(website: str) -> str | None:
    if not website:
        return None
    parsed = urlparse(website)
    domain = parsed.netloc or parsed.path
    domain = domain.replace("www.", "")
    return domain if domain else None


def _db_setting(key: str, default: str = "") -> str:
    try:
        from database import execute
        rs = execute("SELECT value FROM settings WHERE key = ?", [key])
        return rs.rows[0][0] if rs.rows else default
    except Exception:
        return default


def search_hunter(website: str) -> list[dict]:
    """Use Hunter.io to find HR-related emails for a company domain.

    Returns list of {"email", "confidence", "source"}
    """
    if _db_setting("hunter_enabled", "true") == "false":
        return []
    # Check DB first, then env var
    api_key = _db_setting("hunter_api_key") or os.environ.get("HUNTER_API_KEY", "").strip()
    if not api_key:
        logger.warning("HUNTER_API_KEY not set, skipping Hunter.io")
        return []

    domain = _domain_from_url(website)
    if not domain:
        return []

    results = []

    try:
        # Domain search — find all known emails for this domain
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={
                "domain": domain,
                "api_key": api_key,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})

        pattern = data.get("pattern")

        for email_obj in data.get("emails", []):
            email = email_obj.get("value", "").lower()
            if not email:
                continue

            position = (email_obj.get("position") or "").lower()
            first_name = email_obj.get("first_name", "")
            last_name = email_obj.get("last_name", "")
            hunter_confidence = email_obj.get("confidence", 0)

            is_hr = any(
                t in position for t in [
                    "hr", "human resource", "recruit", "talent",
                    "people", "hiring", "staffing", "benefits",
                    "wellness", "employee experience", "employee health",
                    "office manager",
                ]
            )

            if is_hr:
                confidence = "high" if hunter_confidence >= 80 else "medium"
                name_str = f"{first_name} {last_name}".strip()
                source = f"Hunter.io - {position}"
                if name_str:
                    source += f" ({name_str})"
            else:
                confidence = "low"
                name_str = f"{first_name} {last_name}".strip()
                pos_str = position or "employee"
                source = f"Hunter.io - {pos_str}"
                if name_str:
                    source += f" ({name_str})"

            results.append({"email": email, "confidence": confidence, "source": source})

        # Try common HR email patterns and verify them
        for prefix in ["hr", "careers", "jobs", "recruiting"]:
            generic_email = f"{prefix}@{domain}"
            if any(r["email"] == generic_email for r in results):
                continue
            try:
                verify_resp = requests.get(
                    "https://api.hunter.io/v2/email-verifier",
                    params={"email": generic_email, "api_key": api_key},
                    timeout=10,
                )
                if verify_resp.status_code == 200:
                    v_data = verify_resp.json().get("data", {})
                    status = v_data.get("status", "")
                    if status in ("valid", "accept_all"):
                        confidence = "high" if prefix in ("hr", "careers") else "medium"
                        results.append({
                            "email": generic_email,
                            "confidence": confidence,
                            "source": f"Hunter.io - Verified {prefix}@ pattern",
                        })
            except Exception:
                pass

    except Exception as e:
        logger.error("Hunter.io error for %s: %s", domain, e)

    return results


def search_apollo(company_name: str, website: str) -> list[dict]:
    """Use Apollo.io to find HR contacts at a company.

    Uses the new api_search endpoint. On free tier, emails may not be
    available but we get names + titles which can be combined with
    Hunter.io's email pattern to construct likely HR emails.

    Returns list of {"email", "confidence", "source"}
    """
    if _db_setting("apollo_enabled", "true") == "false":
        return []
    api_key = _db_setting("apollo_api_key") or os.environ.get("APOLLO_API_KEY", "").strip()
    if not api_key:
        logger.warning("APOLLO_API_KEY not set, skipping Apollo.io")
        return []

    domain = _domain_from_url(website)
    results = []

    try:
        resp = requests.post(
            "https://api.apollo.io/api/v1/mixed_people/api_search",
            headers={
                "Content-Type": "application/json",
                "X-Api-Key": api_key,
            },
            json={
                "person_titles": HR_TITLES,
                "q_organization_domains": domain or "",
                "page": 1,
                "per_page": 10,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        for person in data.get("people", []):
            email = (person.get("email") or "").lower()
            first_name = person.get("first_name", "")
            last_name_hint = person.get("last_name_obfuscated", "")
            title = person.get("title", "")

            title_lower = title.lower()
            is_strong_hr = any(t in title_lower for t in [
                "human resources", "hr director", "hr manager", "chief people",
                "head of hr", "vp of hr", "head of people",
            ])
            is_weak_hr = any(t in title_lower for t in [
                "recruit", "talent", "people", "hiring",
            ])

            name_display = first_name
            if last_name_hint:
                name_display += f" {last_name_hint}."

            if email:
                # Got an actual email (paid tier)
                confidence = "high" if is_strong_hr else ("medium" if is_weak_hr else "low")
                source = f"Apollo.io - {name_display}, {title}"
                results.append({"email": email, "confidence": confidence, "source": source})
            elif first_name and domain:
                # Free tier: no email, but we know the person exists.
                # Try first@ pattern (safest guess with just a first name)
                guesses = [
                    f"{first_name.lower()}@{domain}",
                ]
                # Only add firstl@ if last_name_hint is a clean single letter (not obfuscated)
                if last_name_hint and len(last_name_hint) == 1 and last_name_hint.isalpha():
                    guesses.append(f"{first_name.lower()}{last_name_hint.lower()}@{domain}")

                for guess in guesses:
                    confidence = "medium" if is_strong_hr else "low"
                    source = f"Apollo.io (guessed) - {name_display}, {title}"
                    results.append({"email": guess, "confidence": confidence, "source": source})

    except Exception as e:
        logger.error("Apollo.io error for %s: %s", company_name, e)

    return results


def find_hr_emails(company_name: str, website: str) -> list[dict]:
    """Run all email finders and merge results.

    Returns deduplicated list sorted by confidence.
    """
    from scraper import scrape_company, _confidence_rank

    all_results = {}

    # 1. Hunter.io (domain-based)
    for item in search_hunter(website):
        email = item["email"]
        if email not in all_results or _confidence_rank(item["confidence"]) > _confidence_rank(all_results[email]["confidence"]):
            all_results[email] = item

    # 2. Apollo.io (people-based)
    for item in search_apollo(company_name, website):
        email = item["email"]
        if email not in all_results or _confidence_rank(item["confidence"]) > _confidence_rank(all_results[email]["confidence"]):
            all_results[email] = item

    # 3. Website scraping (fallback)
    if _db_setting("scraping_enabled", "true") != "false":
        for item in scrape_company(website):
            email = item["email"]
            if email not in all_results or _confidence_rank(item["confidence"]) > _confidence_rank(all_results[email]["confidence"]):
                all_results[email] = item

    return sorted(all_results.values(), key=lambda r: _confidence_rank(r["confidence"]), reverse=True)
