from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from friendslist.auth_helpers import get_credentials
from friendslist.config import config

logger = logging.getLogger(__name__)


def get_events(addresses_dict: dict[str, str]) -> list[dict]:
    creds = get_credentials()
    try:
        service = build("calendar", "v3", credentials=creds)
        now = datetime.now(tz=timezone.utc)
        logger.debug("Getting the upcoming events over the next two weeks...")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=datetime.combine(now, time.min, tzinfo=ZoneInfo("UTC")).isoformat(),
                timeMax=(
                    datetime.now(tz=timezone.utc)
                    + timedelta(days=config["server"]["delta_days"])
                ).isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

        def process_item(item):
            start_date = datetime.fromisoformat(
                item.get("start", {}).get("dateTime")
                or item.get("start", {}).get("date")
            )
            end_date = datetime.fromisoformat(
                item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
            )
            # if it's only a date (no time), return just the date part.
            if item.get("start", {}).get("date"):
                start_date = start_date.date()
            if item.get("end", {}).get("date"):
                end_date = end_date.date()
            return {
                "title": item["summary"],
                "creator": addresses_dict.get(item["creator"]["email"]),
                "start_date": start_date,
                "end_date": end_date,
            }

        return [process_item(item) for item in events_result.get("items", [])]
    except HttpError as error:
        logger.error("An error occurred: %s", error)
        return []
