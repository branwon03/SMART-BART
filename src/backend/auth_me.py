"""
This is a utility script to generate the token.json file for Gmail API authentication.
Running this script is a one time process to authenticate your Gmail account and create the token.json file in the /config directory.
Make sure you have a 'gmail_credentials.json' file in the /config directory before running this. 
"""

from google_auth_oauthlib.flow import InstalledAppFlow
import os

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def generate_token():
    # Ensure the directory exists locally before writing
    os.makedirs('config', exist_ok=True) 
    
    flow = InstalledAppFlow.from_client_secrets_file('config/gmail_credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    
    with open('config/token.json', 'w') as token:
        token.write(creds.to_json())
    print("Success! token.json created in /config.")

if __name__ == '__main__':
    generate_token()