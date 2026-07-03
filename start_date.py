import datetime
import sqlite3

from db import get_start_date, update_start_date
from config import config

DB_PATH = config["server"]["db_path"]


class StartDate:
    """
    Class to manage a start date and check if a specified delta has elapsed.

    Assumes a start date is seeded in the database.
    """

    def __init__(self, conn, delta_days):
        self.date = get_start_date(conn)
        self.delta_days = delta_days

    def advance_date(self, conn):
        self.date += datetime.timedelta(days=self.delta_days)
        update_start_date(conn, self.date)

    def target_date(self):
        return self.date + datetime.timedelta(days=self.delta_days)

    def delta_has_elapsed(self):
        return datetime.date.today() >= self.target_date()
