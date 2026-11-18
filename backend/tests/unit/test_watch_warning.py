import json
from datetime import date

import httpx
import pytest

from sadu.modules.watch.application.ports import AlertMessage
from sadu.modules.watch.domain.change import Threat, Zone
from sadu.modules.watch.domain.risk import RiskLevel
from sadu.modules.watch.domain.warning import Confidence, Reading, Trend, needs_notice, warn
from sadu.modules.watch.infrastructure.notifier import WebhookNotifier

TODAY = date(2026, 11, 18)
WEEK_AGO = date(2026, 11, 11)
BUILDING = frozenset({(Threat.CONSTRUCTION, Zone.RING)})
WATER = frozenset({(Threat.WATER, Zone.INSIDE)})


def test_a_single_moderate_sighting_waits_for_confirmation():
    first = warn([Reading(40, RiskLevel.MODERATE, BUILDING, TODAY)])
    assert first is not None
    assert (first.trend, first.confidence, first.alert) == (Trend.NEW, Confidence.FIRST_SIGHTING, False)


def test_the_same_change_on_two_scans_raises_a_confirmed_alert():
    warning = warn(
        [Reading(45, RiskLevel.MODERATE, BUILDING, TODAY), Reading(20, RiskLevel.WATCH, BUILDING, WEEK_AGO)]
    )
    assert warning is not None
    assert warning.confidence is Confidence.CONFIRMED and warning.alert
    assert warning.trend is Trend.RISING and warning.confirmed_threats == BUILDING


def test_a_different_change_is_not_a_confirmation():
    warning = warn(
        [Reading(45, RiskLevel.MODERATE, WATER, TODAY), Reading(40, RiskLevel.MODERATE, BUILDING, WEEK_AGO)]
    )
    assert warning is not None
    assert warning.confidence is Confidence.FIRST_SIGHTING and not warning.alert
    assert warning.trend is Trend.STEADY


def test_a_rescan_of_the_same_imagery_is_not_a_confirmation():
    same_day = [
        Reading(45, RiskLevel.MODERATE, BUILDING, TODAY),
        Reading(44, RiskLevel.MODERATE, BUILDING, TODAY),
    ]
    warning = warn(same_day)
    assert warning is not None and warning.confidence is Confidence.FIRST_SIGHTING and not warning.alert


def test_specialists_are_told_once_per_alert():
    alerting = [
        Reading(45, RiskLevel.MODERATE, BUILDING, TODAY),
        Reading(40, RiskLevel.MODERATE, BUILDING, WEEK_AGO),
    ]
    assert needs_notice(alerting)
    still = [Reading(46, RiskLevel.MODERATE, BUILDING, date(2026, 11, 25)), *alerting]
    assert not needs_notice(still)


def test_urgent_alerts_do_not_wait():
    warning = warn([Reading(80, RiskLevel.URGENT, WATER, TODAY)])
    assert warning is not None and warning.alert
    assert warn([]) is None


@pytest.mark.anyio
async def test_the_webhook_carries_an_arabic_summary_and_a_link():
    sent: list[dict] = []

    def handle(request: httpx.Request) -> httpx.Response:
        sent.append(json.loads(request.content))
        return httpx.Response(200)

    notifier = WebhookNotifier("https://hooks.test/athar", transport=httpx.MockTransport(handle))
    await notifier.notify(AlertMessage("قرية سدوس", "عاجل", 100, ("حفر",), "rising", "https://athar.test/x"))
    [payload] = sent
    assert payload["site"] == "قرية سدوس" and payload["threats"] == ["حفر"]
    assert "https://athar.test/x" in payload["text"]


@pytest.mark.anyio
async def test_a_failing_webhook_never_breaks_the_scan():
    notifier = WebhookNotifier(
        "https://hooks.test/athar", transport=httpx.MockTransport(lambda r: httpx.Response(500))
    )
    await notifier.notify(AlertMessage("موقع", "متوسط", 40, (), "steady", "https://athar.test/x"))
