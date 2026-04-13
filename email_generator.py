"""AI-powered email generation using Claude for Boob Bus outreach."""

import os
import logging

import anthropic

logger = logging.getLogger(__name__)

BOOB_BUS_CONTEXT = """
The Boob Bus is a mobile 3D mammography service that brings FDA-approved breast cancer screening directly to Utah workplaces. Key facts:

- FDA-approved 3D tomosynthesis (the gold standard in mammography)
- The bus comes directly to the company's parking lot -- employees step out for ~20 minutes
- No referral needed
- Results in 7-14 days
- 4.9/5 stars with 2,400+ reviews
- Cost: $349 per screening (accepted: insurance, HSA, cash, credit, UBCCP vouchers)
- Founded by Rena Vanzo and Mike Koch
- Serves Utah communities
- Mammograms are recommended annually for women 40+ (and earlier for high-risk)

Benefits for companies:
- Shows employees the company cares about their health
- Convenient -- no time off needed for doctor visits
- Early detection saves lives and reduces long-term healthcare costs
- Great for employee wellness programs
- Easy to set up -- we handle everything
- Can be paired with health fairs, wellness days, or benefits enrollment
"""

DEFAULT_PROMPTS = {
    "initial": """Write a short, warm, professional outreach email to pitch The Boob Bus mobile mammography service to this company.

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
- If you know the contact's name, use it. If not, use a warm generic greeting.""",

    "follow_up": """Write a brief follow-up email for The Boob Bus mobile mammography service. This is a follow-up to an initial outreach that got no response.

Target: {contact_info}
Company: {company_name}
Industry: {company_industry}
City: {company_city}

Guidelines:
- Keep it under 100 words
- Reference that you reached out before
- Add one new angle or benefit not in a typical first email
- Mention a specific upcoming availability or seasonal relevance (e.g., Breast Cancer Awareness Month, new year wellness programs, spring health fairs)
- Keep it light, no guilt or pressure
- End with a simple question to prompt a reply""",

    "follow_up_2": """Write a second follow-up email for The Boob Bus mobile mammography service. The recipient hasn't responded to two previous emails.

Target: {contact_info}
Company: {company_name}
Industry: {company_industry}
City: {company_city}

Guidelines:
- Keep it under 100 words
- Don't repeat the same points from earlier emails
- Try a completely different angle (e.g., a success story, a statistic about early detection, or a limited-time offer)
- Very casual and friendly tone
- End with an easy yes/no question""",

    "follow_up_3": """Write a third follow-up email for The Boob Bus mobile mammography service. This is a late-stage follow-up after multiple emails with no response.

Target: {contact_info}
Company: {company_name}
Industry: {company_industry}
City: {company_city}

Guidelines:
- Keep it under 80 words
- Ultra brief and friendly
- Share one compelling stat or testimonial
- Make it feel like a quick note, not a formal email
- End with a simple one-line ask""",

    "final": """Write a final check-in email for The Boob Bus mobile mammography service. This is the last follow-up after no response to previous emails.

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
- Make it easy to say yes with a one-line reply""",
}

# Mapping from sequence step names to prompt keys
STEP_TO_PROMPT_KEY = {
    "initial": "initial",
    "follow_up": "follow_up",
    "follow_up_1": "follow_up",
    "follow_up_2": "follow_up_2",
    "follow_up_3": "follow_up_3",
    "final": "final",
}


def _get_db_setting(key, default=""):
    try:
        from database import execute as db_execute
        rs = db_execute("SELECT value FROM settings WHERE key = ?", [key])
        return rs.rows[0][0] if rs.rows else default
    except Exception:
        return default


def get_prompt(email_type: str) -> str:
    """Get the prompt template for an email type, checking DB first."""
    prompt_key = STEP_TO_PROMPT_KEY.get(email_type, email_type)
    db_key = f"prompt_{prompt_key}"
    custom = _get_db_setting(db_key)
    if custom:
        return custom
    return DEFAULT_PROMPTS.get(prompt_key, DEFAULT_PROMPTS["follow_up"])


def get_all_prompts() -> dict:
    """Get all prompt templates (custom or default)."""
    result = {}
    for key in DEFAULT_PROMPTS:
        custom = _get_db_setting(f"prompt_{key}")
        result[key] = custom if custom else DEFAULT_PROMPTS[key]
    return result


def _get_previous_emails(contact_email: str, company_id: int | None = None) -> str:
    """Fetch previously sent emails to this contact for context."""
    try:
        from database import execute as db_execute
        if company_id:
            rs = db_execute(
                """SELECT email_type, subject, body FROM sent_emails
                   WHERE to_email = ? AND company_id = ?
                   ORDER BY sent_at ASC""",
                [contact_email, company_id],
            )
        else:
            rs = db_execute(
                "SELECT email_type, subject, body FROM sent_emails WHERE to_email = ? ORDER BY sent_at ASC",
                [contact_email],
            )
        if not rs.rows:
            return ""

        parts = []
        for r in rs.rows:
            parts.append(f"--- Previously sent ({r[0]}) ---\nSubject: {r[1]}\n\n{r[2]}")
        return "\n\n".join(parts)
    except Exception:
        return ""


def generate_outreach_email(
    company_name: str,
    company_industry: str,
    company_city: str,
    contact_email: str,
    contact_name: str | None = None,
    contact_title: str | None = None,
    email_type: str = "initial",
    company_id: int | None = None,
    sender_name: str | None = None,
    days_since_last: int | None = None,
) -> dict:
    """Generate a personalized outreach email using Claude."""
    api_key = _get_db_setting("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    client = anthropic.Anthropic(api_key=api_key)

    contact_info = contact_email
    if contact_name:
        contact_info = f"{contact_name} ({contact_email})"
    if contact_title:
        contact_info += f", {contact_title}"

    # Get the prompt template and fill in variables
    prompt_template = get_prompt(email_type)
    prompt = prompt_template.format(
        contact_info=contact_info,
        company_name=company_name,
        company_industry=company_industry,
        company_city=company_city,
    )

    # Add sender name context
    if sender_name:
        prompt += f"\n\nSign off as: {sender_name}, The Boob Bus team"
    else:
        prompt += "\n\nSign off as: The Boob Bus team"

    # For follow-ups, include timing and previous emails
    if email_type != "initial":
        if days_since_last is not None:
            if days_since_last <= 2:
                prompt += f"\n\nThe previous email was sent {days_since_last} day(s) ago. Reference this correctly (e.g., 'I reached out a couple days ago')."
            elif days_since_last <= 7:
                prompt += f"\n\nThe previous email was sent {days_since_last} days ago. Reference this correctly (e.g., 'I reached out earlier this week' or 'a few days ago')."
            else:
                weeks = days_since_last // 7
                prompt += f"\n\nThe previous email was sent {days_since_last} days ago (~{weeks} week(s)). Reference this correctly."

        previous = _get_previous_emails(contact_email, company_id)
        if previous:
            prompt += f"\n\nHere are the emails previously sent to this contact. Do NOT repeat the same points, angles, or phrasing. Write something genuinely different:\n\n{previous}"

    # Use custom Boob Bus info from database if available
    context = _get_db_setting("boobbus_info") or BOOB_BUS_CONTEXT

    # Load customer feedback if available
    feedback = _get_db_setting("customer_feedback")
    feedback_section = ""
    if feedback:
        feedback_section = f"""

CUSTOMER FEEDBACK & TESTIMONIALS (you may reference these, but do NOT fabricate new ones):
{feedback}
"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        system=f"""You are writing outreach emails on behalf of The Boob Bus, a mobile mammography service in Utah.

{context}
{feedback_section}

CRITICAL RULES:
- NEVER make up statistics, dollar amounts, quotes, stories, or testimonials. Only use facts explicitly provided above.
- NEVER mention "special rates", "discounts", or "limited time offers" unless explicitly stated in the info above.
- NEVER use em-dashes or en-dashes (-- or the unicode characters). Use commas, periods, or "and" instead.
- NEVER sign off as "[Your name]" or "[Your Name]". Use the sender name provided in the prompt.
- Keep punctuation simple and clean.
- Most customers pay nothing out of pocket because insurance covers the screening. Mention this.

Return ONLY the email in this exact format:
Subject: [subject line here]

[email body here]

Do not include any other text, explanation, or commentary.""",
        messages=[{"role": "user", "content": prompt}],
    )

    # Parse subject and body from response
    text = message.content[0].text.strip()

    # Post-processing: remove any em-dashes or en-dashes that slipped through
    text = text.replace("\u2014", ", ").replace("\u2013", "-").replace(" -- ", ", ")

    lines = text.split("\n", 1)
    subject = ""
    body = text

    if lines[0].lower().startswith("subject:"):
        subject = lines[0].replace("Subject:", "").replace("subject:", "").strip()
        body = lines[1].strip() if len(lines) > 1 else ""

    # Clean dashes from subject too
    subject = subject.replace("\u2014", ", ").replace("\u2013", "-")
    body = body.replace("\u2014", ", ").replace("\u2013", "-")

    return {"subject": subject, "body": body}
