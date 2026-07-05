from jinja2 import Environment, FileSystemLoader

from config import config

env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("base.html.jinja")
CALENDAR_URL = config["calendar"]["url"]


def render_email_body(date, messages, calendar_html):
    output = template.render(date=date, messages=messages, calendar_html=calendar_html, calendar_url=CALENDAR_URL)

    return output
