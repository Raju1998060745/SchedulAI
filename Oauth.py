from flask import Flask, redirect, url_for, request, jsonify
from google_auth_oauthlib.flow import Flow
import uuid
from db import DBSession
from models import UserToken
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from datetime import datetime
import os, json
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

app = Flask(__name__)
CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "openid"
]
state_map = {}  # To store state and session token mapping

with open("credentials.json", "r") as f:
    credsjson = json.load(f)

client_id = credsjson["web"]["client_id"]
client_secret = credsjson["web"]["client_secret"]


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # 👈 allows http:// for localhost

@app.route("/login")
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES
    )
    flow.redirect_uri = url_for("oauth2callback", _external=True)

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    session_token = str(uuid.uuid4())
    state_map[state] = session_token

    print("[LOGIN] Generated state:", state)
    print("[LOGIN] Session token:", session_token)

    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    state = request.args.get("state")
    code = request.args.get("code")

    print("[CALLBACK] state returned:", state)
    print("[CALLBACK] code returned:", code)

    if state not in state_map:
        return "Invalid or expired state. Please try logging in again.", 400

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = url_for("oauth2callback", _external=True)

    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        return f"Token exchange failed: {e}", 400

    creds = flow.credentials

    # 🔁 Refresh token if needed
    if not creds.valid or creds.expired:
        creds.refresh(Request())

    # ✅ Correct way to fetch user info
    
    headers = {"Authorization": f"Bearer {creds.token}"}
    user_info_response = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers)
    if user_info_response.status_code != 200:
        return f"Failed to fetch user info: {user_info_response.text}", 401

    user_info = user_info_response.json()
    user_id = user_info["email"]

    # Save to DB
    db_session = DBSession()
    token_entry = db_session.query(UserToken).filter_by(user_id=user_id).first()
    if not token_entry:
        token_entry = UserToken(user_id=user_id)

    token_entry.access_token = creds.token
    token_entry.refresh_token = creds.refresh_token
    token_entry.token_expiry = creds.expiry
    token_entry.scopes = ",".join(creds.scopes)

    db_session.add(token_entry)
    db_session.commit()

    print(f"[SUCCESS] Tokens stored for user: {user_id}")
    return f"OAuth completed for {user_id}. You can now use the API."

@app.route("/calendar/<email>")
def get_calendar_events(email):
    db_session = DBSession()
    token_entry = db_session.query(UserToken).filter_by(user_id=email).first()

    if not token_entry:
        return "No token found for this user. Please login first.", 404

   
    creds = Credentials(
        token=token_entry.access_token,
        refresh_token=token_entry.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=token_entry.scopes.split(","),
    )
    print("[DEBUG] token:", creds.token)
    print("[DEBUG] refresh_token:", creds.refresh_token)
    print("[DEBUG] token_uri:", creds.token_uri)
    print("[DEBUG] client_id:", creds.client_id)
    print("[DEBUG] client_secret:", creds.client_secret)
    # Refresh token if expired
    if not creds.valid or creds.expired:
        try:
            creds.refresh(Request())
            token_entry.access_token = creds.token
            token_entry.token_expiry = creds.expiry
            db_session.commit()
            print(f"[INFO] Token refreshed for {email}")
        except Exception as e:
            return f"Failed to refresh token: {e}", 400

    try:
        service = build("calendar", "v3", credentials=creds)
        now = datetime.utcnow().isoformat() + "Z"
        events_result = service.events().list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        events = events_result.get("items", [])
        return jsonify(events)
    except Exception as e:
        return f"Failed to fetch calendar events: {e}", 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
