from datetime import UTC, datetime

from sadu.modules.reports.domain.wall_report import ModelAgreement, ReportCell, WallReport, damage_totals
from sadu.modules.reports.infrastructure.pdf import wall_report_html


def report(**changes) -> WallReport:
    cells = (ReportCell("A1", "crack", "urgent", "model"),)
    base = dict(
        map_id="0f9c2b7e-0000-0000-0000-000000000000",
        wall_name="الواجهة الشمالية",
        site_name="حي الطريف",
        approved=False,
        approved_at=None,
        created_at=datetime(2026, 11, 18, 9, tzinfo=UTC),
        generated_at=datetime(2026, 11, 18, 10, tzinfo=UTC),
        width_m=10.0,
        height_m=6.0,
        rows=8,
        cols=13,
        cell_area_m2=0.58,
        detector="claude",
        overlay_jpeg=b"\xff\xd8\xff",
        damage_colors={"crack": "#c0392b"},
        cells=cells,
        totals=damage_totals(cells, 0.58),
        previous_approved_at=None,
        changes=None,
        treatments=(),
        unmatched=(),
        material_totals=(),
        catalog_version="2026.11-draft",
        catalog_reviewed=False,
        quantities_note_ar="الكميات تقديرية.",
        sources=(),
        agreement=ModelAgreement(1, 1, 0, 0, 0),
    )
    return WallReport(**{**base, **changes})


def test_draft_report_says_it_is_not_approved_and_the_catalog_is_a_draft():
    html = wall_report_html(report())
    assert "هذه مسودة لم يعتمدها خبير بعد" in html
    assert "مسودة لم يراجعها مختص ترميم" in html
    assert "هذا أول مخطط معتمد لهذا الجدار" in html


def test_approved_report_drops_the_draft_warning():
    html = wall_report_html(report(approved=True, approved_at=datetime(2026, 11, 18, 12, tzinfo=UTC)))
    assert "هذه مسودة لم يعتمدها خبير بعد" not in html
    assert "معتمد في ١٨ نوفمبر ٢٠٢٦م" in html


def test_wall_names_are_escaped_and_never_reach_the_page_css():
    html = wall_report_html(report(wall_name='سور-ZX9</h1><script>alert(1)</script>\\"'))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html
    style = html.split("<style>")[1].split("</style>")[0]
    assert "ZX9" not in style
