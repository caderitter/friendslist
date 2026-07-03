import logging
import sqlite3

from imapclient.imapclient import IMAPClient
from auth_helpers import get_credentials
from calendar_helpers import get_events
from config import config
from email_helpers import parse_message_and_save_attachments
from db import get_all_messages_for_delta, init_db, insert_message
from start_date import StartDate

logger = logging.getLogger(__name__)
IMAP_SERVER = config["email"]["imap_server"]
EMAIL_ADDRESS = config["email"]["address"]
DELTA_DAYS = config["server"]["delta_days"]
DB_PATH = config["server"]["db_path"]


def handle_new_message(raw_email_bytes):
    parsed = parse_message_and_save_attachments(raw_email_bytes)
    from_address = parsed["from"]
    subject = parsed["subject"]
    body_plain = parsed["body_plain"]
    body_html = parsed["body_html"]
    attachment_paths = parsed["attachments"]

    logger.info("New email received:")
    logger.info("From: %s", from_address)
    logger.info("Subject: %s", subject)
    logger.info("Body (plain text):\n%s", body_plain)
    logger.info("Body (HTML):\n%s", body_html)
    logger.info("Attachments: %s", attachment_paths)

    try:
        with sqlite3.connect(DB_PATH) as conn:
            insert_message(
                conn, from_address, subject, body_plain, body_html, attachment_paths
            )
            logger.info("Message inserted into the database successfully.")
    except ValueError as e:
        logger.error("Error inserting message: %s", e)


def handle_time_delta_elapsed(start_date):
    logger.info("%d days have passed since the start date", DELTA_DAYS)
    with sqlite3.connect(DB_PATH) as conn:
        events = get_events()
        all_messages = get_all_messages_for_delta(conn, start_date.date, DELTA_DAYS)
        # TODO send email to friends with the messages from the last two weeks
        start_date.advance_date(conn)


def main():
    logging.basicConfig(level=logging.INFO)
    with sqlite3.connect(DB_PATH) as conn:
        init_db(conn)
        start_date = StartDate(conn, DELTA_DAYS)

    creds = get_credentials()

    with IMAPClient(IMAP_SERVER, use_uid=True, ssl=True) as server:
        logger.debug("Logging in to IMAP server...")
        server.oauth2_login(EMAIL_ADDRESS, creds.token)
        server.select_folder("INBOX")
        server.idle()
        logger.info("Listening for new emails...")

        while True:
            responses = server.idle_check(timeout=30)
            if responses:
                server.idle_done()
                messages = server.search(["UNSEEN"])
                for message_data in server.fetch(messages, ["RFC822"]).values():
                    handle_new_message(message_data[b"RFC822"])
                server.idle()
            if start_date.delta_has_elapsed():
                handle_time_delta_elapsed(start_date)


if __name__ == "__main__":
    main()
