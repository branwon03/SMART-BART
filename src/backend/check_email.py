import os.path
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_email_body(payload):
    """Helper function to find and decode the body text from the email payload"""
    # 1. Check if the message is a simple single-part message
    body = payload.get('body', {}).get('data')
    
    # 2. If it's a multipart message (HTML + Text), look through the parts
    if not body and 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain': # We want the plain text version
                body = part.get('body', {}).get('data')
                break
    
    if body:
        # Gmail uses 'urlsafe' base64, so we use this specific decoder
        return base64.urlsafe_b64decode(body).decode('utf-8')
    return "(No text body found)"

def main():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # ===============================================================
            # ENSURE THIS MATCHES YOUR JSON FILENAME
            flow = InstalledAppFlow.from_client_secrets_file('gmail_credentials.json', SCOPES)
            # ===============================================================
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    # Fetching the latest 3 emails (body text gets long, so let's start with 3)
    results = service.users().messages().list(userId='me', maxResults=3).execute()
    messages = results.get('messages', [])

    if not messages:
        print("No messages found.")
    else:
        for msg in messages:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = txt['payload']
            headers = payload['headers']
            
            subject = "No Subject"
            sender = "Unknown"
            for d in headers:
                if d['name'] == 'Subject': subject = d['value']
                if d['name'] == 'From': sender = d['value']
            
            # --- GET THE BODY CONTENT ---
            body_content = get_email_body(payload)
            
            print(f"\n{'='*60}")
            print(f"FROM: {sender}")
            print(f"SUBJECT: {subject}")
            print(f"{'-'*60}")
            print(f"BODY:\n{body_content}")
            print(f"{'='*60}\n")

if __name__ == '__main__':
    main()