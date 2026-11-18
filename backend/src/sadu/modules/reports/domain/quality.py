from dataclasses import dataclass

EVIDENCE_TARGET = 1.0


@dataclass(frozen=True)
class Ratio:
    hits: int
    total: int

    @property
    def value(self) -> float | None:
        return self.hits / self.total if self.total else None

    def meets(self, target: float) -> bool | None:
        value = self.value
        return None if value is None else value >= target


@dataclass(frozen=True)
class QualityReport:
    findings_with_evidence: Ratio
    maps_with_evidence: Ratio
    photos_held_back: Ratio
    findings_held_for_specialist: Ratio
    specialist_rejections: Ratio
    maps_corrected_by_specialist: Ratio

    @property
    def every_report_has_evidence(self) -> bool | None:
        checks = [
            ratio.meets(EVIDENCE_TARGET) for ratio in (self.findings_with_evidence, self.maps_with_evidence)
        ]
        measured = [check for check in checks if check is not None]
        return all(measured) if measured else None


@dataclass(frozen=True)
class QualityInputs:
    published_findings: int
    published_findings_with_evidence: int
    findings_pending_review: int
    findings_rejected: int
    specialist_reviews: int
    specialist_rejections: int
    approved_maps: int
    approved_maps_with_evidence: int
    maps_corrected_by_specialist: int
    photos_finished: int
    photos_sent_back: int


def build_quality_report(inputs: QualityInputs) -> QualityReport:
    all_findings = inputs.published_findings + inputs.findings_pending_review + inputs.findings_rejected
    return QualityReport(
        findings_with_evidence=Ratio(inputs.published_findings_with_evidence, inputs.published_findings),
        maps_with_evidence=Ratio(inputs.approved_maps_with_evidence, inputs.approved_maps),
        photos_held_back=Ratio(inputs.photos_sent_back, inputs.photos_finished),
        findings_held_for_specialist=Ratio(
            inputs.findings_pending_review + inputs.findings_rejected, all_findings
        ),
        specialist_rejections=Ratio(inputs.specialist_rejections, inputs.specialist_reviews),
        maps_corrected_by_specialist=Ratio(inputs.maps_corrected_by_specialist, inputs.approved_maps),
    )
