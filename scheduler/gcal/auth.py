from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar"]  # full read/write access


def authenticate(credentials_file: str = "credentials.json"):
    """
    Authenticate with Google Calendar API via OAuth2.
    Opens a browser for the user to log in and grant access.
    Returns a Google API service object.
    """
    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
    creds = flow.run_local_server(port=0)
    return build("calendar", "v3", credentials=creds)
