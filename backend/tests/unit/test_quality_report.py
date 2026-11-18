from sadu.modules.reports.domain.quality import QualityInputs, Ratio, build_quality_report


def inputs(**overrides: int) -> QualityInputs:
    values = {
        "published_findings": 4,
        "published_findings_with_evidence": 4,
        "findings_pending_review": 1,
        "findings_rejected": 1,
        "specialist_reviews": 3,
        "specialist_rejections": 1,
        "approved_maps": 2,
        "approved_maps_with_evidence": 2,
        "maps_corrected_by_specialist": 1,
        "photos_finished": 10,
        "photos_sent_back": 3,
    }
    return QualityInputs(**(values | overrides))


def test_ratios_come_from_the_counts():
    report = build_quality_report(inputs())
    assert report.findings_with_evidence == Ratio(4, 4)
    assert report.photos_held_back.value == 0.3
    assert report.findings_held_for_specialist == Ratio(2, 6)
    assert report.specialist_rejections == Ratio(1, 3)
    assert report.maps_corrected_by_specialist.value == 0.5
    assert report.every_report_has_evidence is True


def test_one_report_without_evidence_fails_the_target():
    report = build_quality_report(inputs(approved_maps_with_evidence=1))
    assert report.every_report_has_evidence is False


def test_nothing_measured_is_neither_pass_nor_fail():
    report = build_quality_report(
        inputs(
            published_findings=0,
            published_findings_with_evidence=0,
            approved_maps=0,
            approved_maps_with_evidence=0,
            maps_corrected_by_specialist=0,
        )
    )
    assert report.findings_with_evidence.value is None
    assert report.every_report_has_evidence is None


def test_only_measured_sources_count_toward_the_target():
    report = build_quality_report(inputs(published_findings=0, published_findings_with_evidence=0))
    assert report.every_report_has_evidence is True
