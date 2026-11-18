import base64
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from weasyprint import HTML
from weasyprint.urls import URLFetcher

from sadu.modules.reports.application.site_condition import SiteCondition
from sadu.modules.reports.domain import arabic
from sadu.modules.reports.domain.wall_report import WallReport

TEMPLATES = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    autoescape=select_autoescape(default=True, default_for_string=True),
    undefined=StrictUndefined,
)
TEMPLATES.globals.update(
    digits=arabic.digits,
    number=arabic.number,
    percent=arabic.percent,
    date=arabic.date_ar,
    damage=lambda code: arabic.DAMAGE_TYPE_AR.get(code, code),
    severity=lambda code: arabic.SEVERITY_AR.get(code, code),
    source=lambda code: arabic.SOURCE_AR.get(code, code),
    damage_class=lambda code: arabic.CLASS_AR.get(code, code) if code else "—",
    change=lambda code: arabic.CHANGE_AR.get(code, code),
    detector=lambda code: arabic.DETECTOR_AR.get(code, code),
    wall_status=lambda code: arabic.WALL_STATUS_AR.get(code, code),
)


def wall_report_html(report: WallReport) -> str:
    overlay = base64.b64encode(report.overlay_jpeg).decode("ascii")
    return TEMPLATES.get_template("wall_report.html.j2").render(r=report, overlay=overlay)


def site_condition_html(condition: SiteCondition) -> str:
    return TEMPLATES.get_template("site_condition.html.j2").render(c=condition)


def render_pdf(html: str) -> bytes:
    fetcher = URLFetcher(allowed_protocols={"data"}, allow_redirects=False, timeout=1)
    pdf = HTML(string=html, base_url=None, url_fetcher=fetcher).write_pdf()
    if not isinstance(pdf, bytes):
        raise RuntimeError("WeasyPrint returned no PDF")
    return pdf
