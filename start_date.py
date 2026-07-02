import datetime

from db import get_start_date, update_start_date


class StartDate:
    """
    Class to manage a start date and check if a specified delta has elapsed.

    Assumes a start date is seeded in the database.
    """

    def __init__(self, delta_days):
        self.date = get_start_date()
        self.delta_days = delta_days

    def advance_date(self):
        self.date += datetime.timedelta(days=self.delta_days)
        update_start_date(self.date)

    def target_date(self):
        return self.date + datetime.timedelta(days=self.delta_days)

    def delta_has_elapsed(self):
        return datetime.date.today() >= self.target_date()
