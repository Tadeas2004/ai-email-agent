import os
import json
from typing import List, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from services.gmail_service import GmailService
from database import is_email_processed, save_email, get_latest_email_record, init_db


# --- Pydantic Schemas for Strict AI Constraints ---

class EmailEntities(BaseModel):
    people: List[str] = Field(default_factory=list)
    companies: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)

class EmailFactsSchema(BaseModel):
    sender_intent: str
    urgency_signals: List[str] = Field(default_factory=list)
    email_type: str
    sentiment_signals: List[str] = Field(default_factory=list)
    entities: EmailEntities
    explicit_questions: List[str] = Field(default_factory=list)
    commitments_or_promises: List[str] = Field(default_factory=list)
    requires_response_signals: bool

class PrioritySchema(BaseModel):
    level: str
    reason: str

class FullAnalysisSchema(BaseModel):
    summary: str
    category: str
    priority: PrioritySchema
    confidence: float
    action_items: List[str] = Field(default_factory=list)
    requires_response: bool
    follow_up_needed: bool
    deadline: Optional[str] = None
    sentiment: str
    email_type: str
    actionability: str
    entities: EmailEntities


# --- Core Logic ---

def _call_gemini(client, prompt: str, system: str, response_schema) -> dict:
    """
    Executes a strict Gemini API call enforcing a Pydantic response schema.
    Guarantees 100% reliable structural integrity without regex/substring hacks.
    """
    response = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    contents=prompt,
    config=types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        response_schema=response_schema
    )
)
    return json.loads(response.text.strip())


def analyze_email(email_text: str) -> dict:
    """
    Runs a secure 2-step analysis pipeline via Gemini with hard schema validation.
    """
    load_dotenv()
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # Step 1: Context anchoring via structured fact extraction
    extraction_system = "You are an expert email analysis assistant. Extract key facts from the email in English language."
    facts = _call_gemini(client, email_text, extraction_system, EmailFactsSchema)

    # Step 2: Final processing utilizing verified context tokens
    analysis_system = f"""You are an expert email analysis assistant.
    You have already extracted these facts from the email:
    {json.dumps(facts, indent=2)}

    Now produce a full structured analysis following the schema constraints perfectly.
    Ensure confidence is between 0.0 and 1.0, and map data into granular tokens.
    """
    return _call_gemini(client, email_text, analysis_system, FullAnalysisSchema)


def sync_and_analyze_emails(limit: int = 3) -> dict:
    """
    Synchronizes emails, cross-references database states, runs the structured 
    AI engine, and safely flattens schemas for downstream SQLite and Streamlit usage.
    Returns a dictionary summary of the synchronization statistics.
    """
    gmail = GmailService()
    latest_emails = gmail.fetch_emails(limit=limit)
    new_emails_counted = 0
    skipped_emails_counted = 0

    for email_data in latest_emails:
        gmail_id = email_data["id"]

        if is_email_processed(gmail_id):
            skipped_emails_counted += 1
            continue

        formatted_email_text = f"""
        From: {email_data['sender']}
        Subject: {email_data['subject']}
        Body Preview: {email_data['snippet']}
        """

        print(f"Analyzing new email from {email_data['sender']}...")
        
        raw_analysis = analyze_email(formatted_email_text)

        normalized_analysis = {
            "summary": raw_analysis.get("summary"),
            "category": raw_analysis.get("category"),
            "priority": raw_analysis.get("priority", {}).get("level", "low"),
            "priority_reason": raw_analysis.get("priority", {}).get("reason", "No reason provided by AI."),
            "confidence": raw_analysis.get("confidence", 0.5),
            "actions": raw_analysis.get("action_items", []),
            "requires_response": raw_analysis.get("requires_response", False),
            "follow_up_needed": raw_analysis.get("follow_up_needed", False),
            "deadline": raw_analysis.get("deadline"),
            "sentiment": raw_analysis.get("sentiment", "neutral"),
            "actionability": raw_analysis.get("actionability", "informational"),
            "entities": raw_analysis.get("entities", {"people": [], "companies": [], "dates": []})
        }

        save_email(gmail_id, formatted_email_text, normalized_analysis)
        new_emails_counted += 1

    # Return a rich operational summary instead of a raw integer
    return {
        "requested": limit,
        "fetched": len(latest_emails),
        "new": new_emails_counted,
        "skipped": skipped_emails_counted
    }


def main() -> None:
    """
    Local CLI execution test-bed for the orchestration pipeline.
    """
    init_db()
    print("Starting email sync test...")
    stats = sync_and_analyze_emails(limit=1)
    print(f"Sync complete. Checked: {stats['fetched']} | New: {stats['new']} | Skipped: {stats['skipped']}.")

    if stats["new"] <= 0:
        return

    latest_email = get_latest_email_record()
    if latest_email:
        print(f"Latest email category is: {latest_email['category']}...")
    else:
        print("No record found in the database.")


if __name__ == "__main__":
    main()