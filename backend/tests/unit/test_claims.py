import json

import pytest

from sadu.modules.verification.application.claims import check_claims
from sadu.modules.verification.domain.claims import (
    Chunk,
    Claim,
    ClaimLabel,
    SourceKind,
    verbatim_fallback,
)
from tests.fakes import FakeLLM

pytestmark = pytest.mark.anyio

OFFICIAL = Chunk("c1", "s1", SourceKind.OFFICIAL, "بُني الجدار من اللبن والتبن.  وسُقف بجذوع الأثل.")
ORAL = Chunk("c2", "s2", SourceKind.ORAL_REVIEWED, "يذكر الرواة أن السوق كان يُعقد يوم الجمعة.")


def supports(*claim_ids: str):
    def respond(request):
        pairs = json.loads(request.text)
        return {
            "results": [{"claim_id": p["claim_id"], "supported": p["claim_id"] in claim_ids} for p in pairs]
        }

    return respond


async def test_supported_claims_take_their_label_from_the_source_kind():
    claims = [Claim("a", "الجدار من اللبن", "c1"), Claim("b", "السوق يوم الجمعة", "c2")]
    verdicts = await check_claims(FakeLLM(supports("a", "b")), claims, [OFFICIAL, ORAL])
    assert [(v.claim_id, v.label, v.source_id) for v in verdicts] == [
        ("a", ClaimLabel.CONFIRMED, "s1"),
        ("b", ClaimLabel.ORAL_ACCOUNT, "s2"),
    ]


async def test_unsupported_and_uncited_claims_are_unknown():
    claims = [Claim("a", "بُني عام 1850", "c1"), Claim("b", "نص بلا مصدر", None), Claim("c", "x", "missing")]
    llm = FakeLLM(supports())
    verdicts = await check_claims(llm, claims, [OFFICIAL])
    assert all(v.label is ClaimLabel.UNKNOWN and not v.publishable for v in verdicts)
    assert len(json.loads(llm.requests[0].text)) == 1


async def test_nothing_cited_skips_the_model():
    llm = FakeLLM(supports())
    verdicts = await check_claims(llm, [Claim("a", "نص", None)], [OFFICIAL])
    assert llm.requests == []
    assert not verdicts[0].supported


async def test_model_outage_keeps_only_verbatim_official_quotes():
    claims = [
        Claim("quote", "بُني الجدار من اللبن والتبن.", "c1"),
        Claim("paraphrase", "الجدار طيني", "c1"),
        Claim("oral", "السوق كان يُعقد يوم الجمعة", "c2"),
    ]
    verdicts = await check_claims(FakeLLM(None), claims, [OFFICIAL, ORAL])
    assert [v.publishable for v in verdicts] == [True, False, False]


def test_verbatim_match_ignores_whitespace_differences():
    claim = Claim("q", "بُني الجدار من اللبن والتبن. وسُقف", "c1")
    assert verbatim_fallback([claim], [OFFICIAL])[0].label is ClaimLabel.CONFIRMED
