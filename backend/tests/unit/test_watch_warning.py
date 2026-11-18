import json

import httpx
import pytest

from sadu.modules.watch.application.ports import AlertMessage
from sadu.modules.watch.domain.change import Threat, Zone
from sadu.modules.watch.domain.risk import RiskLevel
from sadu.modules.watch.domain.warning import Confidence, Reading, Trend, warn
from sadu.modules.watch.infrastructure.notifier import WebhookNotifier

BUILDING = frozenset({(Threat.CONSTRUCTION, Zone.RING)})
WATER = frozenset({(Threat.WATER, Zone.INSIDE)})


def test_a_single_moderate_sighting_waits_for_confirmation():
    first = warn([Reading(40, RiskLevel.MODERATE, BUILDING)])
    assert first is not None
    assert (first.trend, first.confidence, first.alert) == (Trend.NEW, Confidence.FIRST_SIGHTING, False)


def test_the_same_change_on_two_scans_raises_a_confirmed_alert():
    warning = warn([Reading(45, RiskLevel.MODERATE, BUILDING), Reading(20, RiskLevel.WATCH, BUILDING)])
    assert warning is not None
    assert warning.confidence is Confidence.CONFIRMED and warning.alert
    assert warning.trend is Trend.RISING and warning.confirmed_threats == BUILDING


def test_a_different_change_is_not_a_confirmation():
    warning = warn([Reading(45, RiskLevel.MODERATE, WATER), Reading(40, RiskLevel.MODERATE, BUILDING)])
    assert warning is not None
    assert warning.confidence is Confidence.FIRST_SIGHTING and not warning.alert
    assert warning.trend is Trend.STEADY


def test_urgent_alerts_do_not_wait():
    warning = warn([Reading(80, RiskLevel.URGENT, WATER)])
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
