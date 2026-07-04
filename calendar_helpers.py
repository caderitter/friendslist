import datetime
import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth_helpers import get_credentials
from config import config

logger = logging.getLogger(__name__)


def get_events():
    creds = get_credentials()
    try:
        service = build("calendar", "v3", credentials=creds)
        now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        logger.debug("Getting the upcoming events over the next two weeks...")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                timeMax=(
                    datetime.datetime.now(tz=datetime.timezone.utc)
                    + datetime.timedelta(days=config["server"]["delta_days"])
                ).isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return [
            {
                "title": item["summary"],
                "creator": item["creator"]["email"],
                "start_date": item["start"]["date"],
                "end_date": item["end"]["date"],
            }
            for item in events_result.get("items", [])
        ]
    except HttpError as error:
        logger.error("An error occurred: %s", error)
        return []
