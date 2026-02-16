"""One-time Google OAuth setup script.

Run this to authorize the assistant with your Google account.
It will open a browser for you to sign in, then save the credentials
to backend/data/google-credentials.json.

Usage:
    cd backend
    uv run python scripts/google_auth_setup.py
"""

import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.modify",
]

# Find the client secret file
BACKEND_DIR = Path(__file__).resolve().parent.parent
CLIENT_SECRET_FILES = list(BACKEND_DIR.glob("client_secret*.json"))

if not CLIENT_SECRET_FILES:
    print("No client_secret*.json file found in backend/.")
    print("Download one from Google Cloud Console > APIs & Services > Credentials.")
    raise SystemExit(1)

client_secret_path = CLIENT_SECRET_FILES[0]
print(f"Using client secret: {client_secret_path.name}")

# Run the OAuth flow
flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), SCOPES)
creds = flow.run_local_server(port=0)

# Save credentials
output_path = BACKEND_DIR / "data" / "google-credentials.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
creds_data = json.loads(creds.to_json())
creds_data["type"] = "authorized_user"
output_path.write_text(json.dumps(creds_data, indent=2))

print(f"\nCredentials saved to: {output_path}")
print(f"\nUpdate your .env file:")
print(f"  ASSISTANT_GOOGLE_CREDENTIALS_PATH={output_path}")
