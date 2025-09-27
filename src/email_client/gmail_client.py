import os
import json
import base64
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class GmailClient:
    def __init__(self):
        self.creds = None
        self.service = None

    def authenticate(self):
        creds_json = os.getenv('GMAIL_CREDENTIALS_JSON')
        token_json = os.getenv('GMAIL_TOKEN_JSON')

        if not creds_json or not token_json:
            raise Exception("Missing Gmail credentials or token environment variables")

        # Parse JSON strings
        token_dict = json.loads(token_json)

        self.creds = Credentials.from_authorized_user_info(token_dict, scopes=SCOPES)

        # Refresh token if expired
        if self.creds and self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
            # Optionally save updated token JSON somewhere safe

        self.service = build('gmail', 'v1', credentials=self.creds)
        logger.info("Authenticated and Gmail service initialized.")

    def list_recent_emails(self, max_results=5, label_ids=['INBOX'], query=None):
        try:
            request_params = {
                'userId': 'me',
                'labelIds': label_ids,
                'maxResults': max_results
            }
            if query:
                request_params['q'] = query

            results = self.service.users().messages().list(**request_params).execute()
            messages = results.get('messages', [])
            emails = []

            for msg in messages:
                msg_data = self.service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                headers = msg_data.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
                snippet = msg_data.get('snippet', '')
                emails.append({'id': msg['id'], 'subject': subject, 'snippet': snippet})

            return emails
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return []

    def get_email_body(self, msg_id):
        try:
            msg_data = self.service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            payload = msg_data.get('payload', {})
            parts = payload.get('parts', [])
            body = ""

            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        decoded = base64.urlsafe_b64decode(data).decode('utf-8')
                        body += decoded
                    break

            if not body:
                body_data = payload.get('body', {}).get('data')
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')

            return body
        except Exception as e:
            logger.error(f"Error fetching email body: {e}")
            return ""
