import calendar
from datetime import date, datetime, time, timedelta
from collections import defaultdict

WEEKDAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

DEFAULT_EVENT_COLOR = "#4a6fa5"


def _is_all_day(ev: dict) -> bool:
    return not isinstance(ev["start_date"], datetime)


def _event_start_date(ev: dict) -> date:
    sd = ev["start_date"]
    return sd.date() if isinstance(sd, datetime) else sd


def _event_end_date(ev: dict) -> date:
    ed = ev["end_date"]
    return ed.date() if isinstance(ed, datetime) else ed


def _format_time(t: time) -> str:
    hour12 = t.strftime("%I").lstrip("0") or "12"
    return f"{hour12}:{t.strftime('%M %p')}"


def _title_with_time(ev: dict) -> str:
    """'Creator: Title', plus the start time appended after it if timed."""
    label = f"{ev['creator']}: {ev.get('title', '')}"
    if not _is_all_day(ev):
        label += (
            f' <span class="event-time">{_format_time(ev["start_date"].time())}</span>'
        )
    return label


def build_two_week_calendar(start_sunday: date, events: list[dict]) -> str:
    if start_sunday.weekday() != 6:  # Python: Monday=0 ... Sunday=6
        raise ValueError(
            f"start_sunday must be a Sunday, got {start_sunday} "
            f"({calendar.day_name[start_sunday.weekday()]})"
        )

    # expand each event across every day it covers (multi-day events just
    # get placed on each day in their range).
    events_by_day = defaultdict(list)
    for ev in events:
        ev_start, ev_end = _event_start_date(ev), _event_end_date(ev)
        num_days = (ev_end - ev_start).days
        for i in range(num_days + 1):
            events_by_day[ev_start + timedelta(days=i)].append(ev)

    days = [start_sunday + timedelta(days=i) for i in range(14)]
    weeks = [days[0:7], days[7:14]]

    today = date.today()

    header_cells = "".join(f"<th>{label}</th>" for label in WEEKDAY_LABELS)

    def render_day_cell(d: date) -> str:
        classes = ["day-cell"]
        if d == today:
            classes.append("today")
        if d.month != start_sunday.month:
            classes.append("other-month")

        day_events = sorted(
            events_by_day.get(d, []),
            key=lambda e: (
                e["start_date"].time() if not _is_all_day(e) else time.min,
                e.get("title", ""),
            ),
        )

        day_events_html = ""
        for ev in day_events:
            color = ev.get("color", DEFAULT_EVENT_COLOR)
            if _is_all_day(ev):
                day_events_html += (
                    f'<div class="event event-all-day" style="background:{color};">'
                    f"{_title_with_time(ev)}</div>"
                )
            else:
                day_events_html += (
                    f'<div class="event" style="background:{color}22;'
                    f'border-left:3px solid {color};">{_title_with_time(ev)}</div>'
                )

        return (
            f'<td class="{" ".join(classes)}">'
            f'<div class="day-number">{d.day}</div>'
            f'<div class="events" style="flex-direction: column; gap: 3px;">{day_events_html}</div>'
            f"</td>"
        )

    weeks_html = ""
    for week in weeks:
        row = "".join(render_day_cell(d) for d in week)
        weeks_html += f"<tr>{row}</tr>"

    end_date = days[-1]
    title_range = f"{start_sunday.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')}"

    html = f"""
        <div class="calendar-wrapper">
            <div class="calendar-title">{title_range}</div>
            <table>
                <thead><tr>{header_cells}</tr></thead>
                <tbody>{weeks_html}</tbody>
            </table>
        </div>
    """
    return html
