import base64
import email
import io
import logging
import os
import smtplib
from email.header import decode_header, make_header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr, parsedate_to_datetime

from PIL import Image

from friendslist.auth_helpers import get_credentials
from friendslist.config import config

logger = logging.getLogger(__name__)
EMAIL_ADDRESS = config["email"]["address"]
SMTP_SERVER = config["email"]["smtp_server"]


def extract_attachment(part, content_type, content_disposition):
    logger.debug("Extracting attachment...")
    is_attachment = (
        "attachment" in content_disposition or "inline" in content_disposition
    )
    is_image = content_type.startswith("image/")
    if not (is_attachment and is_image):
        return None
    filename = part.get_filename()
    if not filename:
        return None
    filename_header = str(make_header(decode_header(filename)))
    filepath = os.path.join("attachments", filename_header)
    base, extension = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(filepath):
        filepath = f"{base}_{counter}{extension}"
        counter += 1
    payload = part.get_payload(decode=True)
    if payload is None:
        return None
    img = Image.open(io.BytesIO(payload))
    rgb_img = img.convert("RGB")
    rgb_img.save(filepath, format="JPEG", quality=30)
    logger.info("Saved attachment: %s", filepath)
    return filepath


def parse_message_and_save_attachments(raw_email_bytes):
    logger.debug("Parsing email...")
    msg = email.message_from_bytes(raw_email_bytes, policy=email.policy.default)

    subject = msg["Subject"]
    raw_from = msg["From"]
    _, sender_address = parseaddr(raw_from)
    date = parsedate_to_datetime(msg["date"])

    body_plain = ""
    body_html = ""

    saved_paths = []

    for part in msg.walk():
        content_type = part.get_content_type()
        content_disposition = str(part.get("Content-Disposition") or "")

        saved_path = extract_attachment(part, content_type, content_disposition)
        if saved_path:
            saved_paths.append(saved_path)

        if content_type == "text/plain" and not body_plain:
            charset = part.get_content_charset() or "utf-8"
            body_plain = part.get_payload(decode=True).decode(charset, errors="replace")

        elif content_type == "text/html" and not body_html:
            charset = part.get_content_charset() or "utf-8"
            body_html = part.get_payload(decode=True).decode(charset, errors="replace")

    return {
        "subject": subject,
        "from": sender_address,
        "body_plain": body_plain,
        "body_html": body_html,
        "attachments": saved_paths,
        "date": date,
    }


def send_email(
    to_addresses: list[str], subject: str, body_html: str, attachments: tuple[str, str]
):
    creds = get_credentials()
    msg = MIMEMultipart("related")
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = ", ".join(to_addresses)
    msg["Subject"] = subject

    html = MIMEText(body_html, "html")

    msg.attach(html)

    for image_id, path in attachments:
        with open(path, "rb") as f:
            img_data = f.read()
            img = MIMEImage(img_data)
            img.add_header("Content-ID", f"<{image_id}>")
            img.add_header(
                "Content-Disposition", "inline", filename=os.path.basename(path)
            )
            msg.attach(img)

    creds = get_credentials()
    auth_string = f"user={EMAIL_ADDRESS}\1auth=Bearer {creds.token}\1\1"
    smtp_conn = smtplib.SMTP_SSL(SMTP_SERVER, 465)
    smtp_conn.ehlo()

    smtp_conn.docmd(
        "AUTH", "XOAUTH2 " + base64.b64encode(auth_string.encode()).decode()
    )
    smtp_conn.sendmail(EMAIL_ADDRESS, to_addresses, msg.as_string())
    smtp_conn.quit()
