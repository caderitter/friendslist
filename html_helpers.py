from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("base.html.jinja")


def render_email_body(date, messages):
    output = template.render(date=date, messages=messages)

    return output
