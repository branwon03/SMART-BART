import os.path
import base64
import requests
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# --- CONFIGURATION ---
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
API_BASE_URL = "http://localhost:8000/api"
STATIONS = [
    "12th St. Oakland City Center", "16th St. Mission", "19th St. Oakland", "24th St. Mission",
    "Antioch", "Ashby", "Balboa Park", "Bay Fair", "Berryessa / North San Jose",
    "Castro Valley", "Civic Center / UN Plaza", "Coliseum", "Colma", "Concord",
    "Daly City", "Downtown Berkeley", "Dublin / Pleasanton", "El Cerrito del Norte",
    "El Cerrito Plaza", "Embarcadero", "Fremont", "Fruitvale", "Glen Park", "Hayward",
    "Lafayette", "Lake Merritt", "MacArthur", "Millbrae", "Milpitas", "Montgomery St.",
    "North Berkeley", "North Concord / Martinez", "Oakland International Airport",
    "Orinda", "Pittsburg / Bay Point", "Pittsburg Center", "Pleasant Hill / Contra Costa Centre",
    "Powell St.", "Richmond", "Rockridge", "San Bruno", "San Francisco International Airport",
    "San Leandro", "South Hayward", "South San Francisco", "Union City", "Walnut Creek",
    "Warm Springs / South Fremont", "West Dublin / Pleasanton", "West Oakland"
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
    results = service.users().messages().list(userId='me', q='label:INBOX').execute()
    messages = results.get('messages', [])

    for msg_ref in messages:
        full_msg = service.users().messages().get(userId='me', id=msg_ref['id']).execute()
        thread_id = full_msg['threadId']
        snippet = full_msg.get('snippet', '')

        # Find Images
        payload = full_msg.get('payload', {})
        parts = payload.get('parts', [])
        
        def find_images(parts_list):
            imgs = []
            for part in parts_list:
                if part.get('parts'): imgs.extend(find_images(part['parts']))
                filename = part.get('filename')
                if filename and part.get('mimeType', '').startswith('image/'):
                    att = service.users().messages().attachments().get(
                        userId='me', messageId=msg_ref['id'], id=part['body']['attachmentId']
                    ).execute()
                    imgs.append(('media', (filename, base64.urlsafe_b64decode(att['data']), part['mimeType'])))
            return imgs

        image_files = find_images(parts)

        # LOGIC A: NEW REPORT
        if image_files:
            print(f"Relaying new report from thread: {thread_id}")
            form_data = {
                "description": snippet,
                "photo_location_id": "EMAIL-Unlocated", # Explicitly set as unlocated
                "gmail_thread_id": thread_id            # Hidden link for later
            }
            r = requests.post(f"{API_BASE_URL}/submissions", files=image_files, data=form_data)
            
            if r.status_code == 200:
                inc_id = r.json().get('incident_id')
                station_list = "\n".join([f"- {s}" for s in STATIONS])
                reply_body = f"Report Received (ID: {inc_id}).\n\nPlease reply with your BART Station name:\n\n{station_list}"
                service.users().messages().send(userId='me', body=create_reply(full_msg, reply_body)).execute()
                service.users().messages().modify(userId='me', id=msg_ref['id'], body={'removeLabelIds': ['INBOX']}).execute()

        # LOGIC B: STATION UPDATE REPLY
        else:
            matched_station = next((s for s in STATIONS if s.lower() in snippet.lower()), None)
            if matched_station:
                print(f"Station reply detected: {matched_station}")
                
                # Fetch incidents and find the one with this thread_id
                incidents = requests.get(f"{API_BASE_URL}/incidents").json()
                target = next((i for i in incidents if i.get('gmail_thread_id') == thread_id), None)
                
                if target:
                    print(f"Found incident {target['incident_id']}. Updating location...")
                    update_data = {
                        "status": "In Progress",
                        "issue_priority": "Standard",
                        "location_id": matched_station # Overwrite 'EMAIL-Unlocated'
                    }
                    requests.put(f"{API_BASE_URL}/incidents/{target['incident_id']}", json=update_data)
                    
                    # Notify user and Archive
                    service.users().messages().send(userId='me', body=create_reply(full_msg, f"Updated location to: {matched_station}")).execute()
                    service.users().messages().modify(userId='me', id=msg_ref['id'], body={'removeLabelIds': ['INBOX']}).execute()
                else:
                    print("Matched station but couldn't find a corresponding incident thread in DB.")

if __name__ == '__main__':
    main()