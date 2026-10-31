from routing.domain.recommend import RouteCandidate, explain, rank, summarize_risk
from routing.domain.risk import RiskLevel

L, M, H, S, N = (
    RiskLevel.LOW,
    RiskLevel.MODERATE,
    RiskLevel.HIGH,
    RiskLevel.SEVERE,
    RiskLevel.NO_TRAVEL,
)


def candidate(levels: list[RiskLevel], hours: float, step: float = 10) -> RouteCandidate:
    risk = summarize_risk([(i * step, level) for i, level in enumerate(levels)])
    return RouteCandidate(risk=risk, duration_s=hours * 3600)


def test_segment_takes_worse_endpoint() -> None:
    risk = summarize_risk([(0, L), (10, H), (20, L), (30, L)])
    assert risk.miles(H) == 20
    assert risk.miles(L) == 10
    assert risk.average_risk == (20 * 2 + 10 * 0) / 30
    assert risk.max_level is H


def test_fewest_severe_miles_beats_fewer_high_and_faster() -> None:
    severe = candidate([L, S, L, L], hours=10)
    high = candidate([H, H, H, H], hours=14)
    assert rank([severe, high]) == [1, 0]
    assert "Severe" in explain(high, severe)


def test_fewest_high_miles_when_severe_ties() -> None:
    a = candidate([L, H, H, L], hours=10)
    b = candidate([L, H, L, L], hours=12)
    assert rank([a, b]) == [1, 0]


def test_average_risk_when_severe_and_high_tie() -> None:
    a = candidate([M, M, M, M], hours=10)
    b = candidate([L, L, M, L], hours=12)
    assert rank([a, b]) == [1, 0]
    assert "average risk" in explain(b, a)


def test_travel_time_breaks_full_tie() -> None:
    a = candidate([L, L, L], hours=12)
    b = candidate([L, L, L], hours=10)
    assert rank([a, b]) == [1, 0]
    assert "travel time" in explain(b, a)


def test_no_travel_ranks_last() -> None:
    blocked = candidate([L, N, L, L], hours=8)
    severe = candidate([S, S, S, S], hours=20)
    assert rank([blocked, severe]) == [1, 0]
