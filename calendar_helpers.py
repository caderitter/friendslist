import datetime
import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth_helpers import get_credentials
from config import config

logger = logging.getLogger(__name__)


def get_events(addresses_dict: dict[str, str]) -> list[dict]:
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

        def process_item(item):
            start_date = datetime.datetime.fromisoformat(
                item.get("start", {}).get("dateTime")
                or item.get("start", {}).get("date")
            )
            end_date = datetime.datetime.fromisoformat(
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

        items = events_result.get("items", [])
        return list(map(process_item, items))
    except HttpError as error:
        logger.error("An error occurred: %s", error)
        return []
