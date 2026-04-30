import os.path
import base64
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
API_URL = "http://localhost:8000/api/submissions"

def main():
    creds = None
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
        # Get the full message
        full_msg = service.users().messages().get(userId='me', id=msg['id']).execute()
        email_description = full_msg.get('snippet', 'No description provided.')

        # FIND IMAGES
        payload = full_msg.get('payload', {})
        parts = payload.get('parts', [])
        image_files = []

        for part in parts:
            filename = part.get('filename')
            mime_type = part.get('mimeType')
            
            if filename and mime_type and mime_type.startswith('image/'):
                # Download and Decode Attachment
                att_id = part['body'].get('attachmentId')
                attachment = service.users().messages().attachments().get(
                    userId='me', messageId=msg['id'], id=att_id
                ).execute()
                
                file_data = base64.urlsafe_b64decode(attachment['data'])
                image_files.append(('media', (filename, file_data, mime_type)))

        # POST TO FASTAPI
        if image_files:
            print(f"Relaying email: {email_description[:30]}...")
            form_data = {
                "description": email_description,
                "photo_location_id": "GMAIL_INTAKE"
            }
            try:
                r = requests.post(API_URL, files=image_files, data=form_data)
                print(f"Status {r.status_code}: {r.json().get('incident_id')}")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == '__main__':
    main()