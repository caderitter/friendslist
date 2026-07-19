from jinja2 import Environment, FileSystemLoader

from config import config

env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("base.html.jinja")
CALENDAR_URL = config["calendar"]["url"]


def render_email_body(date, messages, cal_title_range, cal_weeks):
    output = template.render(
        date=date,
        messages=messages,
        calendar_url=CALENDAR_URL,
        title_range=cal_title_range,
        weeks=cal_weeks,
    )

    return output
