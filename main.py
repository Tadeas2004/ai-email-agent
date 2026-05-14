import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from services.gmail_service import GmailService
from database import is_email_processed, save_email, get_latest_email_record, init_db


def _call_gemini(client, prompt: str, system: str) -> dict:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system)
    )
    # Robustly extract JSON from response regardless of markdown fences
    text = response.text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


def analyze_email(email: str) -> dict:
    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # Step 1: Extract key facts from the email
    extraction_system = """You are an expert email analysis assistant.
    Extract key facts from the email. Return ONLY valid JSON, no extra text:
    {
        "sender_intent": "what the sender wants or is communicating",
        "urgency_signals": ["list of phrases or signals indicating urgency"],
        "email_type": "question|request|complaint|invoice|update|approval|scheduling|other",
        "sentiment_signals": ["list of emotional or tonal cues detected"],
        "entities": {
            "people": ["names mentioned"],
            "companies": ["companies or organizations mentioned"],
            "dates": ["dates, deadlines or time references mentioned"]
        },
        "explicit_questions": ["list of direct questions the sender is asking"],
        "commitments_or_promises": ["anything the sender is committing to or promising"],
        "requires_response_signals": "boolean - true if sender clearly expects a reply, false if not"
    }"""

    facts = _call_gemini(client, email, extraction_system)

    # Step 2: Use extracted facts to produce a full structured analysis
    analysis_system = f"""You are an expert email analysis assistant.
    You have already extracted these facts from the email:
    {json.dumps(facts, indent=2)}

    Now produce a full structured analysis. Return ONLY valid JSON, no extra text:
    {{
        "summary": "2-3 sentence summary of the email",
        "category": "invoice|inquiry|complaint|meeting_request|internal_update|legal|newsletter|spam|urgent_issue|follow_up|project_update|other",
        "priority": {{
            "level": "high|medium|low",
            "reason": "one sentence explaining why this priority level was chosen"
        }},
        "confidence": "number between 0.0 and 1.0 reflecting certainty of this analysis",
        "action_items": ["specific action 1", "specific action 2"],
        "requires_response": "boolean - true if sender expects a reply, false if not",
        "follow_up_needed": "boolean - true if recipient is waiting on someone else to respond, false if not",
        "deadline": "ISO date string if detected, otherwise null",
        "sentiment": "positive|neutral|negative|urgent|frustrated|friendly",
        "email_type": "question|request|complaint|invoice|update|approval|scheduling|other",
        "actionability": "actionable|informational|blocking|waiting_on_me|waiting_on_them|delegated",
        "entities": {{
            "people": ["list of names mentioned"],
            "companies": ["list of companies mentioned"],
            "dates": ["list of dates or deadlines mentioned"]
        }}
    }}

    Rules:
    - confidence should reflect how certain you are about priority and category (0.0 = uncertain, 1.0 = very certain)
    - requires_response = true if the sender expects a reply from the recipient
    - follow_up_needed = true if the recipient sent something previously and is still waiting on a response
    - deadline = extract any explicit or implicit deadlines, return null if none detected
    - actionability reflects the operational state of this email
    - be specific in action_items, avoid vague suggestions like "reply to email"
    """

    return _call_gemini(client, email, analysis_system)

def sync_and_analyze_emails(limit: int = 5) -> int:
    """
    Fetches latest emails, checks for duplicates, analyzes new ones, 
    and saves them to the database. Returns the number of newly analyzed emails.
    """
    gmail = GmailService()
    latest_emails = gmail.fetch_emails(limit=limit)
    new_emails_counted = 0

    for email_data in latest_emails:
        gmail_id = email_data["id"]

        # Skip if we already handled this email
        if is_email_processed(gmail_id):
            continue

        # Format a clean string combining metadata and content for Gemini
        formatted_email_text = f"""
        From: {email_data['sender']}
        Subject: {email_data['subject']}
        Body Preview: {email_data['snippet']}
        """

        print(f"Analyzing new email from {email_data['sender']}...")
        
        # Run a 2-step Gemini pipeline
        analysis_result = analyze_email(formatted_email_text)

        # Save to SQLite
        save_email(gmail_id, formatted_email_text, analysis_result)
        new_emails_counted += 1

    return new_emails_counted


def main() -> None:
    init_db()
    print("Starting email sync test...")
    count = sync_and_analyze_emails(limit=1)
    print(f"Sync complete. Analyzed {count} new emails.")

    if count <= 0:
        return

    latest_email = get_latest_email_record()
    if latest_email:
        print(f"Latest email category is: {latest_email['category']}...")
        print(f"Latest email summary is: {latest_email['summary']}...")
    else:
        print("No record found in the database.")


if __name__ == "__main__":
    main()
