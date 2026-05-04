import os.path
import base64
import requests
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 1. SCOPE UPDATED: Needs 'modify' or 'send' to reply
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
API_URL = "http://localhost:8000/api/submissions"

def create_reply(original_msg, body_text):
    """Constructs the reply email structure."""
    message = MIMEText(body_text)
    
    # Extract headers to ensure it threads correctly
    headers = original_msg.get('payload', {}).get('headers', [])
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "")
    msg_id = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), None)
    to_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), None)

    message['To'] = to_email
    message['Subject'] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    if msg_id:
        message['In-Reply-To'] = msg_id
        message['References'] = msg_id

    # Gmail expects base64url encoded string
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw, 'threadId': original_msg['threadId']}

def main():
    creds = None
    # Note: If you already have token.json, delete it and re-run to update scopes
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('gmail_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(userId='me', maxResults=5).execute()
    messages = results.get('messages', [])

    for msg in messages:
        full_msg = service.users().messages().get(userId='me', id=msg['id']).execute()
        email_description = full_msg.get('snippet', 'No description provided.')

        payload = full_msg.get('payload', {})
        parts = payload.get('parts', [])
        image_files = []

        for part in parts:
            filename = part.get('filename')
            mime_type = part.get('mimeType')
            
            if filename and mime_type and mime_type.startswith('image/'):
                att_id = part['body'].get('attachmentId')
                attachment = service.users().messages().attachments().get(
                    userId='me', messageId=msg['id'], id=att_id
                ).execute()
                
                file_data = base64.urlsafe_b64decode(attachment['data'])
                image_files.append(('media', (filename, file_data, mime_type)))

        if image_files:
            print(f"Relaying email: {email_description[:30]}...")
            form_data = {
                "description": email_description,
                "photo_location_id": "GMAIL_INTAKE"
            }
            try:
                r = requests.post(API_URL, files=image_files, data=form_data)
                if r.status_code == 200:
                    incident_id = r.json().get('incident_id')
                    print(f"Success! Incident ID: {incident_id}")

                    # --- SEND THE REPLY ---
                    reply_text = f"Hello, we have received your images. Incident ID: {incident_id} has been created."
                    reply_msg_body = create_reply(full_msg, reply_text)
                    service.users().messages().send(userId='me', body=reply_msg_body).execute()
                    print("Reply sent to user.")
                    
            except Exception as e:
                print(f"Error: {e}")

if __name__ == '__main__':
    main()