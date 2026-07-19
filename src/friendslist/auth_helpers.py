import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from friendslist.config import config

logger = logging.getLogger(__name__)
SCOPES = [config["email"]["scope"], config["calendar"]["scope"]]


def get_credentials() -> Credentials:
    logger.debug("Getting credentials for email access...")
    creds = None
    if os.path.exists("token.json"):
        logger.debug("Loading credentials from token.json...")
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.debug("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            logger.debug("No valid credentials found, initiating OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secrets.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    return creds
