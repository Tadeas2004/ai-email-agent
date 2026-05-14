import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow # type: ignore
from googleapiclient.discovery import build # type: ignore

# Define the scope: readonly allows us to view but not modify or delete emails.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailService:
    def __init__(self):
        """
        Initializes the Gmail service by handling authentication
        and building the API client. Falls back to Mock mode if credentials are missing.
        """
        self.creds = self._authenticate()
        
        if self.creds:
            self.service = build('gmail', 'v1', credentials=self.creds)
            self.is_mock = False
        else:
            self.service = None
            self.is_mock = True
            print("PRODUCTION WARNING: credentials.json not found. Operating in DEMO/MOCK mode with sample data.")

    def _authenticate(self):
        creds = None
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        
        # Join the root directory with the filenames
        token_path = os.path.join(root_dir, 'token.json')
        credentials_path = os.path.join(root_dir, 'credentials.json')

        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None

            if not creds or not creds.valid:
                # CRITICAL CLOUD ISOLATION: If credentials.json is missing (e.g., on Render),
                # do not crash the app, return None to trigger safe Mock/Demo mode.
                if not os.path.exists(credentials_path):
                    return None
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            
            if creds:
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                    
        return creds

    def fetch_emails(self, limit=3):
        """
        Fetches a list of the latest emails. If in mock mode or API fails,
        returns structured, high-quality sample data tailored for Bohemia Interactive presentation.
        """
        if self.is_mock:
            return self._get_mock_emails(limit)

        try:
            # 1. Get the list of message IDs
            response = self.service.users().messages().list(
                userId='me', labelIds=['INBOX'], maxResults=limit
            ).execute()
            messages = response.get('messages', [])

            email_data = []
            for msg in messages:
                # 2. Fetch full message details
                full_msg = self.service.users().messages().get(
                    userId='me', id=msg['id']
                ).execute()
                
                # Extract headers for a more professional input for Gemini
                headers = full_msg.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')

                email_data.append({
                    "id": msg['id'],
                    "sender": sender,
                    "subject": subject,
                    "snippet": full_msg.get('snippet', '')
                })
            
            return email_data

        except Exception as error:
            print(f'An error occurred in GmailService API: {error}. Falling back to demo data.')
            return self._get_mock_emails(limit)

    def _get_mock_emails(self, limit):
        """
        Returns high-quality, realistic tech/gaming emails for demonstration purposes.
        Ensures a fantastic presentation review without exposing private data.
        """
        mock_data = [
            {
            "id": "mock_1",
            "sender": "sandbox.developer@example.com",
            "subject": "Enfusion Engine - Dev Team Update",
            "snippet": "Ahoj, posílám update k integraci skriptů. V nové verzi Enfusion Enginu jsme optimalizovali refaktorizaci herní smyčky a paměťové pooly pro stabilnější renderování textur na Macu."
            },
            {
                "id": "mock_2",
                "sender": "qa.testing.bot@example.com",
                "subject": "DayZ Stability Crash Report - Build #4092",
                "snippet": "CRITICAL ERROR: Server crash detected on Chernarus-12. Exception in memory management during entity serialization. Prosim o urgentni review logu, patch specha."
            },
            {
                "id": "mock_3",
                "sender": "hr.demo@example.com",
                "subject": "Informatics Internship - Tadeas Mutina",
                "snippet": "Dobrý den, posíláme potvrzení o přijetí vaší přihlášky na pozici vývojáře. Váš projektový repozitář s AI agentem v Dockeru předáváme týmu k technickému review."
            },
            {
                "id": "mock_4",
                "sender": "marketing.automation@example.com",
                "subject": "Web Analytics and Tracking Setup Complete",
                "snippet": "Ahoj, GTM (Google Tag Manager) i GA4 tracking tagy jsou nasazené na produkční landing page. Konverze z Meta Ads se už správně propisují do databáze."
            }
        ]
        return mock_data[:limit]

if __name__ == '__main__':
    gmail = GmailService()
    test_emails = gmail.fetch_emails(limit=2)
    for e in test_emails:
        print(f"DEBUG - From: {e['sender']} | Subject: {e['subject']}")