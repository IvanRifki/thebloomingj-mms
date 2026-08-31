from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": "INI_ID_CLIENT",
            "client_secret": "INI_CLIENT_SECRET",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    },
    scopes=SCOPES
)

creds = flow.run_local_server(port=0)

print("\n=== REFRESH TOKEN BARU ===")
print(creds.refresh_token)
print("===========================\n")
