import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape

DEFAULT_EVENT_COLOR = "#4a6fa5"

TEMPLATES_DIR = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
template = env.get_template("calendar.html.jinja")


def build_calendar_props(start_sunday: date, events: list[dict]) -> dict:
    if start_sunday.weekday() != 6:
        raise ValueError(
            f"start_sunday must be a Sunday, got {start_sunday} "
            f"({calendar.day_name[start_sunday.weekday()]})"
        )

    # expand each event across every day it covers (multi-day events just
    # get placed on each day in their range).
    events_by_day = defaultdict(list)
    for ev in events:
        sd = ev["start_date"]
        ed = ev["end_date"]
        ev_start_date = sd.date() if isinstance(sd, datetime) else sd
        ev_end_date = ed.date() if isinstance(ed, datetime) else ed
        num_days = (ev_end_date - ev_start_date).days
        for i in range(num_days + 1):
            events_by_day[ev_start_date + timedelta(days=i)].append(ev)

    days = [start_sunday + timedelta(days=i) for i in range(14)]

    def build_day_context(d: date) -> dict:
        day_events = sorted(
            events_by_day.get(d, []),
            key=lambda e: (
                e["start_date"].time()
                if isinstance(e["start_date"], datetime)
                else time.min,
                e.get("title", ""),
            ),
        )

        def build_event(ev):
            is_all_day = not isinstance(ev["start_date"], datetime)
            event_label = Markup("{}: {}").format(ev["creator"], ev.get("title", ""))

            if not is_all_day:
                ev_time = ev["start_date"].time()
                hour12 = ev_time.strftime("%I").lstrip("0") or "12"
                formatted_time = f"{hour12}:{ev_time.strftime('%M %p')}"
                time_str = escape(formatted_time)
                event_label += Markup(f' <span class="event-time">{time_str}</span>')

            color = ev.get("color", DEFAULT_EVENT_COLOR)
            # solid filled style for all-day events
            event_style = (
                f"background:{color};"
                if is_all_day
                else f"background:{color}22;border-left:3px solid {color};"
            )

            return {
                "all_day": is_all_day,
                "label": event_label,
                "style": event_style,
            }

        return {
            "day_number": d.day,
            "is_today": d == date.today(),
            "is_other_month": d.month != start_sunday.month,
            "events": [build_event(event) for event in day_events],
        }

    weeks = [
        [build_day_context(d) for d in days[0:7]],
        [build_day_context(d) for d in days[7:14]],
    ]

    end_date = days[-1]
    title_range = f"{start_sunday.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"

    return title_range, weeks
