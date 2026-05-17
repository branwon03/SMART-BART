"""
This is a worker script that operates in the background to check for new emails in a Gmail account 
    and process them as maintenance reports. It uses the Gmail API to read emails, extract any attached images, 
    and interact with a backend API to create or update maintenance incidents based on the email content.
"""






import os
import time
import base64
import requests
import re
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Color macros
RED = "\033[91m"
BOLD = "\033[1m"
ENDC = "\033[0m"

# --- CONFIG ---
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api")
POLL_INTERVAL = 5 
STATIONS = [
    "Arts and Computational Sciences", "Bellevue Lot", "Biomedical Sciences and Physics",
    "Bobcat Field", "Cathedral", "Central Utilities Plant", "Classroom and Office Building 1",
    "Classroom and Office Building 2", "El Portal", "Glacier Point", "Granite Pass", "Gym",
    "Half Dome", "Kolligian Library", "Mariposa", "Pavilion Dining Center", "Scholar's Lot",
    "Science and Engineering", "Science and Engineering 2", "Sentinel Rock",
    "Social Sciences and Management", "Student Services Building",
    "Sustainability Research and Engineering", "Tenaya", "Tuolomne", "University Plaza",
    "Valley Terraces", "Yablokoff-Wallace Dining Center"
]

def create_reply(original_msg, body_text):
    message = MIMEText(body_text)
    headers = original_msg.get('payload', {}).get('headers', [])
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), "BART Report")
    msg_id = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), None)
    to_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), None)
    message['To'] = to_email
    message['Subject'] = f"Re: {subject}" if not subject.startswith("Re:") else subject
    if msg_id:
        message['In-Reply-To'] = msg_id
        message['References'] = msg_id
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode(), 'threadId': original_msg['threadId']}

def get_service():
    token_path = 'config/token.json'
    
    if not os.path.exists(token_path):
        print(f"[!] '{token_path}' not found. Please run auth_me.py locally.")
        return None

    try:
        creds = Credentials.from_authorized_user_file(token_path)
        
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        
        return build('gmail', 'v1', credentials=creds)

    except Exception as e:
        print(f"[!] Error loading credentials: {e}")
        return None

def check_and_process():
    service = get_service()
    if service is None:     # If credentials couldn't be loaded, skip processing to avoid errors
        return 
    # Only get UNREAD messages in INBOX to avoid processing the same thing twice
    results = service.users().messages().list(userId='me', q='label:INBOX is:unread').execute()
    messages = results.get('messages', [])

    if not messages:
        return

    for msg_ref in messages:
        full_msg = service.users().messages().get(userId='me', id=msg_ref['id']).execute()
        thread_id = full_msg['threadId']
        snippet = full_msg.get('snippet', '')
        
        # 1. Check for Images (New Intake)
        parts = full_msg.get('payload', {}).get('parts', [])
        image_files = []
        def find_imgs(p_list):
            imgs = []
            for p in p_list:
                if p.get('parts'): 
                    imgs.extend(find_imgs(p['parts']))
                if p.get('filename') and p.get('mimeType', '').startswith('image/'):
                    att = service.users().messages().attachments().get(userId='me', messageId=msg_ref['id'], id=p['body']['attachmentId']).execute()
                    imgs.append(('media', (p['filename'], base64.urlsafe_b64decode(att['data']), p['mimeType'])))
            return imgs
        
        image_files = find_imgs(parts)

        if image_files:
            print(f"[*] New Gmail Intake: {thread_id}")
            data = {"description": snippet, "photo_location_id": "EMAIL-Unlocated", "gmail_thread_id": thread_id}
            r = requests.post(f"{API_BASE_URL}/submissions", files=image_files, data=data)
            if r.status_code == 200:
                body = "Thank you for your submission - it has succesfully processed. To help expedite our maintenance response, please reply with the location name (e.g., 'Granite Pass'):\n\n" + "\n".join([f"- {s}" for s in STATIONS])
                service.users().messages().send(userId='me', body=create_reply(full_msg, body)).execute()
                # Mark as read/remove from inbox
                service.users().messages().modify(userId='me', id=msg_ref['id'], body={'removeLabelIds': ['INBOX', 'UNREAD']}).execute()

        # 2. Check for Station Name (Update)
        else:
            sorted_stations = sorted(STATIONS, key=len, reverse=True)
            matched = None
            for s in sorted_stations:
                # Use regex to find the station name as a whole phrase, ignoring case
                if re.search(rf"\b{re.escape(s)}\b", snippet, re.IGNORECASE):
                    matched = s
                    break

            if matched:
                incidents = requests.get(f"{API_BASE_URL}/incidents").json()
                # Find the most recent incident with this thread ID
                target = next((i for i in reversed(incidents) if i.get('gmail_thread_id') == thread_id), None)
                
                if target:
                    print(f"[*] Updating Location for {target['incident_id']} -> {matched}")
                    update_data = {"location_id": matched}
                    requests.put(f"{API_BASE_URL}/incidents/{target['incident_id']}", json=update_data)
                    
                    reply_text = f"Thank you. Your submission has been updated to include location: {matched}."
                    service.users().messages().send(userId='me', body=create_reply(full_msg, reply_text)).execute()
                    service.users().messages().modify(userId='me', id=msg_ref['id'], body={'removeLabelIds': ['INBOX', 'UNREAD']}).execute()

def run_worker():
    print("[*] Gmail Worker Started. Polling...")
    counter = 0
    
    while True:
        try:
            if (counter % 4) == 0:  # Log every 4 iterations (every 10 seconds) so it isn't spammed
                print("[*] Checking for new emails...")
            check_and_process()
        except Exception as e:
            # Check if it's a DNS/Connection error to keep logs clean
            if ("gmail.googleapis.com" in str(e) and counter % 2):
                print("[!] Worker: Waiting for internet connection...")
            elif counter % 4 == 0:  # Log other errors every 4 iterations to avoid spamming
                print(f"[!] Worker Error: {e}")
        
        time.sleep(POLL_INTERVAL)
        counter += 1

if __name__ == '__main__':
    run_worker()