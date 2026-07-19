from datetime import datetime
import logging
from pprint import pformat

from imapclient.imapclient import IMAPClient

from friendslist.auth_helpers import get_credentials
from friendslist.calendar_helpers import get_events
from friendslist.config import config
from friendslist.db import (
    get_addresses_dict,
    get_all_messages_for_delta,
    get_db_connection,
    init_db,
    insert_message,
)
from friendslist.email_helpers import parse_message_and_save_attachments, send_email
from friendslist.generate_calendar import build_calendar_props
from friendslist.html_helpers import render_email_body
from friendslist.start_date import StartDate

logger = logging.getLogger(__name__)
IMAP_SERVER = config["email"]["imap_server"]
EMAIL_ADDRESS = config["email"]["address"]
DELTA_DAYS = config["server"]["delta_days"]
DB_PATH = config["server"]["db_path"]
FRIENDS_CSV_PATH = config["server"]["friends_csv_path"]


def handle_new_message(raw_email_bytes: bytes):
    parsed = parse_message_and_save_attachments(raw_email_bytes)
    logger.info("New email received: %s", pformat(parsed))

    try:
        with get_db_connection(DB_PATH) as conn:
            insert_message(
                conn=conn,
                received_at=parsed["date"],
                email=parsed["from"],
                subject=parsed["subject"],
                body_plain=parsed["body_plain"],
                body_html=parsed["body_html"],
                attachment_paths=parsed["attachments"],
            )
            logger.info("Message inserted into the database successfully.")
    except ValueError as e:
        logger.error("Error inserting message: %s", e)


def handle_time_delta_elapsed(start_date: StartDate):
    logger.info(
        "%d days have passed since the start date. Sending email...", DELTA_DAYS
    )
    with get_db_connection(DB_PATH) as conn:
        today = datetime.today()
        messages = get_all_messages_for_delta(conn, today, DELTA_DAYS)
        # create array of tuples of (file id, file path) from all the messages
        attachments = [
            (attachment["id"], attachment["file_path"])
            for message in messages
            for attachment in message["attachments"]
        ]
        addresses_dict = get_addresses_dict(conn)
        events = get_events(addresses_dict)
        cal_title_range, cal_weeks = build_calendar_props(
            start_date.date.date(), events
        )
        main_html = render_email_body(
            date=today,
            messages=messages,
            cal_title_range=cal_title_range,
            cal_weeks=cal_weeks,
        )
        subject = f"Glizzy Friendsletter: {today.strftime('%B %e')}"
        # send_email(list(addresses_dict.keys()), subject, main_html, attachments)
        send_email(["ritter.cade@gmail.com"], subject, main_html, attachments)
        # start_date.advance_date(conn)


def main():
    logging.basicConfig(level=logging.INFO)
    with get_db_connection(DB_PATH) as conn:
        init_db(conn, FRIENDS_CSV_PATH)
        start_date = StartDate(conn, DELTA_DAYS)

    creds = get_credentials()

    with IMAPClient(IMAP_SERVER, use_uid=True, ssl=True) as server:
        logger.debug("Logging in to IMAP server...")
        server.oauth2_login(EMAIL_ADDRESS, creds.token)
        server.select_folder("INBOX")
        server.idle()
        logger.info("Listening for new emails...")

        while True:
            try:
                responses = server.idle_check(timeout=30)
                if responses:
                    server.idle_done()
                    messages = server.search(["UNSEEN"])
                    for message_data in server.fetch(messages, ["RFC822"]).values():
                        handle_new_message(message_data[b"RFC822"])
                    server.idle()
                if start_date.delta_has_elapsed():
                    handle_time_delta_elapsed(start_date)
            except Exception as e:
                logger.error("Error: %s", e)

