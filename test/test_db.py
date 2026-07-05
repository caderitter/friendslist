from datetime import datetime, timedelta

import pytest

from db import get_all_messages_for_delta, insert_message


def test_insert_message(db_connection):
    insert_message(
        db_connection,
        "alice@gmail.com",
        "Test subject",
        "Test message",
        "<div>Test message</div>",
        ["attachment.png"],
    )

    cursor = db_connection.cursor()
    cursor.execute(
        """
        SELECT f.name, f.email, m.subject, m.body_plain, m.body_html, a.file_path 
        FROM messages m
        JOIN friends f ON m.friend_id = f.id
        JOIN attachments a ON m.id = a.message_id
    """
    )
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == "Alice"
    assert result[1] == "alice@gmail.com"
    assert result[2] == "Test subject"
    assert result[3] == "Test message"
    assert result[4] == "<div>Test message</div>"
    assert result[5] == "attachment.png"


def test_insert_message_with_stranger_email_raises(db_connection):
    with pytest.raises(ValueError, match="No friend found with email: eve@gmail.com"):
        insert_message(
            db_connection,
            "eve@gmail.com",
            "Test subject",
            "Test message",
            "<div>Test message</div>",
            ["attachment.png"],
        )


def test_get_all_messages_for_delta(db_connection):
    cursor = db_connection.cursor()

    cursor.execute(
        "INSERT INTO messages (friend_id, subject, body_plain, received_at) VALUES (?, ?, ?, ?)",
        (1, "Test subject", "Test message", datetime(2026, 1, 4)),
    )

    cursor.execute(
        "INSERT INTO messages (friend_id, subject, body_plain, received_at) VALUES (?, ?, ?, ?)",
        (
            1,
            "Test subject - too long ago",
            "Test message - too long ago",
            datetime(2026, 1, 1),
        ),
    )

    messages = get_all_messages_for_delta(db_connection, datetime(2026, 1, 7), 5)

    assert len(messages) == 1
    assert messages[0]["subject"] == "Test subject"
    assert messages[0]["body_plain"] == "Test message"

def test_get_all_messages_with_attachments(db_connection):
    insert_message(
        db_connection,
        "alice@gmail.com",
        "Test subject",
        "Test message",
        "<div>Test message</div>",
        ["attachment.png"],
    )
    insert_message(
        db_connection,
        "bob@gmail.com",
        "Test subject",
        "Test message",
        "<div>Test message</div>",
        ["attachment1.png", "attachment2.png"],
    )

    messages = get_all_messages_for_delta(db_connection, datetime.today() + timedelta(days=1), 2)
    assert len(messages) == 2
    first = messages[0]
    second = messages[1]
    assert len(first["attachments"]) == 1
    assert first["attachments"][0]["id"] is not None
    assert first["attachments"][0]["file_path"] == "attachment.png"
    assert len(second["attachments"]) == 2
    assert second["attachments"][0]["id"] is not None
    assert second["attachments"][0]["file_path"] == "attachment1.png"
    assert second["attachments"][1]["id"] is not None
    assert second["attachments"][1]["file_path"] == "attachment2.png"



