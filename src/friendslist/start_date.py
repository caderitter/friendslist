from datetime import datetime, timedelta, time
from sqlite3 import Connection

from friendslist.db import get_start_date, update_start_date


class StartDate:
    """
    Class to manage a start date and check if a specified delta has elapsed.

    Assumes a start date is seeded in the database.
    """

    def __init__(self, conn: Connection, delta_days: int):
        self.date = datetime.combine(get_start_date(conn), time.min)
        self.delta_days = delta_days

    def advance_date(self, conn: Connection):
        self.date += timedelta(days=self.delta_days)
        update_start_date(conn, self.date.date())

    def target_date(self):
        return self.date + timedelta(minutes=5)

    def delta_has_elapsed(self):
        return datetime.today() >= self.target_date()
