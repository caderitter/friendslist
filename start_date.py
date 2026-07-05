from datetime import datetime, timedelta

from db import get_start_date, update_start_date


class StartDate:
    """
    Class to manage a start date and check if a specified delta has elapsed.

    Assumes a start date is seeded in the database.
    """

    def __init__(self, conn, delta_days):
        self.date = datetime.fromisoformat(get_start_date(conn))
        self.delta_days = delta_days

    def advance_date(self, conn):
        self.date += timedelta(days=self.delta_days)
        update_start_date(conn, self.date)

    def target_date(self):
        return self.date + timedelta(days=self.delta_days)

    def delta_has_elapsed(self):
        return datetime.today() >= self.target_date()
