"""AI-powered company suggestion generator for the Boob Bus.

Uses Claude with structured tool_use to produce real Utah companies matching
user-provided filters, then verifies each website with a quick HEAD request.
"""

import os
import logging
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

import anthropic
import requests

logger = logging.getLogger(__name__)


GENERATE_TOOL = {
    "name": "propose_companies",
    "description": "Return a list of real, verifiable Utah companies matching the user's filters.",
    "input_schema": {
        "type": "object",
        "properties": {
            "companies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Official company name."},
                        "website": {"type": "string", "description": "Primary website URL (include https://)."},
                        "industry": {"type": "string", "description": "Concise industry label (e.g. 'Healthcare', 'Manufacturing')."},
                        "city": {"type": "string", "description": "Utah city where headquartered or has a major operation."},
                        "county": {"type": "string", "description": "Utah county name (without the word 'County')."},
                        "estimated_employees": {"type": "string", "description": "Rough employee count range, e.g. '50-200', '500+', 'unknown'."},
                        "reasoning": {"type": "string", "description": "One short sentence on why this company fits the request."},
                    },
                    "required": ["name", "website", "industry", "city", "county"],
                },
            }
        },
        "required": ["companies"],
    },
}


def _get_db_setting(key, default=""):
    try:
        from database import execute as db_execute
        rs = db_execute("SELECT value FROM settings WHERE key = ?", [key])
        return rs.rows[0][0] if rs.rows else default
    except Exception:
        return default


def _build_prompt(
    count: int,
    city: str | None,
    county: str | None,
    industry: str | None,
    min_employees: int | None,
    prioritize_women: bool,
    avoid_keywords: list[str],
    existing_names: list[str],
) -> str:
    lines = [
        f"Generate {count} real Utah companies that could be prospects for The Boob Bus, a mobile 3D mammography service that visits workplaces.",
        "",
        "Filters:",
    ]
    if city:
        lines.append(f"- Located in or near: {city}, Utah")
    if county:
        lines.append(f"- County: {county} County, Utah")
    if industry:
        lines.append(f"- Industry: {industry}")
    if min_employees:
        lines.append(f"- Minimum employee count: ~{min_employees}+ (large enough to justify an on-site mammography visit)")
    if prioritize_women:
        lines.append("- Prioritize workplaces with women-heavy or women-significant workforces (healthcare, education, nonprofits, admin, retail HQs, etc.). The Boob Bus only serves women, so this matters a lot.")
    if avoid_keywords:
        lines.append(f"- AVOID companies related to: {', '.join(avoid_keywords)}")

    lines += [
        "",
        "Hard requirements:",
        "- Only real, existing, verifiable Utah companies. No made-up names or URLs.",
        "- Websites MUST be the company's actual primary domain. If unsure, pick a different company.",
        "- Use canonical https:// URLs.",
        "- Do NOT return single-location tiny shops (under ~20 employees) unless the user explicitly asked for small.",
        "- Do NOT return individual restaurants or retail franchise locations, return the parent/HQ if applicable.",
        "- Return distinct companies, no duplicates.",
    ]
    if existing_names:
        preview = existing_names[:60]
        lines.append("")
        lines.append("DO NOT return any of these companies (already in our database):")
        lines.append(", ".join(preview))
        if len(existing_names) > 60:
            lines.append(f"(...and {len(existing_names) - 60} more — avoid obvious Utah names you'd expect to be in a business database.)")

    lines += [
        "",
        f"Return exactly {count} companies via the propose_companies tool. If you genuinely cannot find {count} that meet the criteria, return fewer rather than making any up.",
    ]
    return "\n".join(lines)


CHUNK_SIZE = 3  # companies per parallel Claude call


def _generate_chunk(
    client,
    chunk_count: int,
    city: str | None,
    county: str | None,
    industry: str | None,
    min_employees: int | None,
    prioritize_women: bool,
    avoid_keywords: list[str],
    existing_names: list[str],
    already_proposed: list[str],
) -> list[dict]:
    """Ask Claude for a single chunk of companies, with web_search enabled."""
    all_avoid = (existing_names or []) + (already_proposed or [])
    prompt = _build_prompt(
        count=chunk_count,
        city=city,
        county=county,
        industry=industry,
        min_employees=min_employees,
        prioritize_women=prioritize_women,
        avoid_keywords=avoid_keywords,
        existing_names=all_avoid,
    )

    # Server-side web_search lets Claude find real URLs instead of hallucinating them.
    # propose_companies is the structured-output tool for the final list.
    web_search_tool = {"type": "web_search_20250305", "name": "web_search", "max_uses": 10}

    prompt_with_instructions = (
        prompt
        + "\n\nCRITICAL: For EVERY company you propose, use web_search to find its actual official website. "
        "Do NOT guess URLs from the company name — hallucinated URLs are the #1 failure mode of this tool. "
        "Search '{company name} utah' and take the real domain from the results. "
        "After gathering real URLs for all companies, call the propose_companies tool with the final list."
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8000,
        tools=[web_search_tool, GENERATE_TOOL],
        messages=[{"role": "user", "content": prompt_with_instructions}],
    )

    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "propose_companies":
            return block.input.get("companies", [])

    # Fallback: Claude didn't call the tool — nudge it
    nudge_messages = [
        {"role": "user", "content": prompt_with_instructions},
        {"role": "assistant", "content": message.content},
        {"role": "user", "content": "Now call the propose_companies tool with the list you found."},
    ]
    follow_up = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        tools=[web_search_tool, GENERATE_TOOL],
        tool_choice={"type": "tool", "name": "propose_companies"},
        messages=nudge_messages,
    )
    for block in follow_up.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "propose_companies":
            return block.input.get("companies", [])
    return []


def generate_companies(
    count: int,
    city: str | None = None,
    county: str | None = None,
    industry: str | None = None,
    min_employees: int | None = 50,
    prioritize_women: bool = False,
    avoid_keywords: list[str] | None = None,
    existing_names: list[str] | None = None,
) -> list[dict]:
    """Ask Claude for N companies, splitting into parallel chunks for speed.

    Each chunk runs as its own Claude call with web_search, so the searches
    across chunks run concurrently instead of serially.
    """
    api_key = _get_db_setting("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)

    # Split count into chunks (≤ CHUNK_SIZE each)
    n_chunks = max(1, (count + CHUNK_SIZE - 1) // CHUNK_SIZE)
    chunk_sizes = [count // n_chunks] * n_chunks
    for i in range(count % n_chunks):
        chunk_sizes[i] += 1

    # Pre-seed each chunk with the already-in-DB names. We can't feed Claude
    # other parallel chunks' output (they run simultaneously), so we accept
    # some cross-chunk duplication and dedupe after.
    existing_names = existing_names or []

    def run_one(size: int) -> list[dict]:
        if size <= 0:
            return []
        try:
            return _generate_chunk(
                client=client,
                chunk_count=size,
                city=city,
                county=county,
                industry=industry,
                min_employees=min_employees,
                prioritize_women=prioritize_women,
                avoid_keywords=avoid_keywords or [],
                existing_names=existing_names,
                already_proposed=[],
            )
        except Exception as e:
            logger.warning("Chunk generation failed: %s", e)
            return []

    # Run chunks in parallel
    all_companies: list[dict] = []
    if n_chunks == 1:
        all_companies = run_one(chunk_sizes[0])
    else:
        with ThreadPoolExecutor(max_workers=min(n_chunks, 6)) as pool:
            for result in pool.map(run_one, chunk_sizes):
                all_companies.extend(result)

    # Dedupe by lower-cased name (different chunks may propose the same company)
    seen = set()
    deduped = []
    for c in all_companies:
        nm = (c.get("name") or "").strip().lower()
        if not nm or nm in seen:
            continue
        seen.add(nm)
        deduped.append(c)

    # If we ended up short due to cross-chunk dupes, that's OK — user asked for up to N
    return deduped[:count]


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def verify_website(url: str, timeout: float = 4.0) -> bool:
    """Quick HTTP check. Returns True if the domain resolves and responds OK."""
    url = _normalize_url(url)
    if not url:
        return False
    parsed = urlparse(url)
    if not parsed.netloc or "." not in parsed.netloc:
        return False

    headers = {"User-Agent": "Mozilla/5.0 (BoobBus verify)"}
    try:
        r = requests.head(url, timeout=timeout, allow_redirects=True, headers=headers)
        if 200 <= r.status_code < 400:
            return True
        # Some sites reject HEAD — retry with GET
        if r.status_code in (400, 403, 405, 501):
            r = requests.get(url, timeout=timeout, allow_redirects=True, headers=headers, stream=True)
            return 200 <= r.status_code < 400
        return False
    except requests.RequestException:
        return False


def verify_websites_parallel(urls: list[str], timeout: float = 4.0) -> list[bool]:
    """Verify multiple URLs in parallel. Returns list of booleans in same order."""
    with ThreadPoolExecutor(max_workers=min(10, max(1, len(urls)))) as pool:
        return list(pool.map(lambda u: verify_website(u, timeout), urls))
