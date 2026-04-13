"""AI-powered email generation using Claude for Boob Bus outreach."""

import os
import logging

import anthropic

logger = logging.getLogger(__name__)

BOOB_BUS_CONTEXT = """
The Boob Bus is a mobile 3D mammography service that brings FDA-approved breast cancer screening directly to Utah workplaces. Key facts:

- FDA-approved 3D tomosynthesis (the gold standard in mammography)
- The bus comes directly to the company's parking lot — employees step out for ~20 minutes
- No referral needed
- Results in 7-14 days
- 4.9/5 stars with 2,400+ reviews
- Cost: $349 per screening (accepted: insurance, HSA, cash, credit, UBCCP vouchers)
- Founded by Rena Vanzo and Mike Koch
- Serves Utah communities
- Mammograms are recommended annually for women 40+ (and earlier for high-risk)

Benefits for companies:
- Shows employees the company cares about their health
- Convenient — no time off needed for doctor visits
- Early detection saves lives and reduces long-term healthcare costs
- Great for employee wellness programs
- Easy to set up — we handle everything
- Can be paired with health fairs, wellness days, or benefits enrollment
"""


def generate_outreach_email(
    company_name: str,
    company_industry: str,
    company_city: str,
    contact_email: str,
    contact_name: str | None = None,
    contact_title: str | None = None,
    email_type: str = "initial",
) -> dict:
    """Generate a personalized outreach email using Claude.

    Args:
        company_name: Target company
        company_industry: Company's industry
        company_city: Company location
        contact_email: Recipient email
        contact_name: Recipient name (if known)
        contact_title: Recipient job title (if known)
        email_type: "initial", "follow_up", or "final"

    Returns:
        {"subject": str, "body": str}
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)

    contact_info = contact_email
    if contact_name:
        contact_info = f"{contact_name} ({contact_email})"
    if contact_title:
        contact_info += f", {contact_title}"

    if email_type == "initial":
        prompt = f"""Write a short, warm, professional outreach email to pitch The Boob Bus mobile mammography service to this company.

Target: {contact_info}
Company: {company_name}
Industry: {company_industry}
City: {company_city}

Guidelines:
- Keep it under 150 words
- Friendly and conversational, not salesy
- Open with something specific to their company or industry if possible
- Mention 2-3 key benefits relevant to their situation
- End with a clear, low-pressure call to action (suggest a quick call or reply)
- Don't use exclamation marks excessively
- Sign off as the Boob Bus team
- If you know the contact's name, use it. If not, use a warm generic greeting."""

    elif email_type == "follow_up":
        prompt = f"""Write a brief follow-up email for The Boob Bus mobile mammography service. This is a follow-up to an initial outreach that got no response.

Target: {contact_info}
Company: {company_name}
Industry: {company_industry}
City: {company_city}

Guidelines:
- Keep it under 100 words
- Reference that you reached out before
- Add one new angle or benefit not in a typical first email
- Mention a specific upcoming availability or seasonal relevance (e.g., Breast Cancer Awareness Month, new year wellness programs, spring health fairs)
- Keep it light — no guilt or pressure
- End with a simple question to prompt a reply"""

    elif email_type == "final":
        prompt = f"""Write a final check-in email for The Boob Bus mobile mammography service. This is the last follow-up after no response to previous emails.

Target: {contact_info}
Company: {company_name}
Industry: {company_industry}
City: {company_city}

Guidelines:
- Keep it under 80 words
- Very brief and respectful
- Acknowledge they're busy
- Leave the door open without pressure
- Mention you won't follow up again unless they're interested
- Make it easy to say yes with a one-line reply"""

    else:
        raise ValueError(f"Unknown email_type: {email_type}")

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=f"""You are writing outreach emails on behalf of The Boob Bus, a mobile mammography service in Utah.

{BOOB_BUS_CONTEXT}

Return ONLY the email in this exact format:
Subject: [subject line here]

[email body here]

Do not include any other text, explanation, or commentary.""",
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse subject and body from response
    text = message.content[0].text.strip()
    lines = text.split("\n", 1)

    subject = ""
    body = text

    if lines[0].lower().startswith("subject:"):
        subject = lines[0].replace("Subject:", "").replace("subject:", "").strip()
        body = lines[1].strip() if len(lines) > 1 else ""

    return {"subject": subject, "body": body}
