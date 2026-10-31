"""Route risk summaries and the recommendation ordering.

Miles at a risk level: the stretch between two consecutive checkpoints takes the worse of
the two checkpoint levels (conservative: a storm at either end counts for the whole stretch).

Ordering, per the brief: fewest Severe miles, fewest High miles, lowest average risk,
shortest travel time. No Travel miles are ranked ahead of all of these, since No Travel is
worse than Severe.
"""

import itertools
from dataclasses import dataclass

from routing.domain.risk import RiskLevel


@dataclass(frozen=True, slots=True)
class RouteRisk:
    miles_by_level: dict[RiskLevel, float]
    average_risk: float
    max_level: RiskLevel

    def miles(self, level: RiskLevel) -> float:
        return self.miles_by_level.get(level, 0.0)


@dataclass(frozen=True, slots=True)
class RouteCandidate:
    risk: RouteRisk
    duration_s: float


def summarize_risk(checkpoints: list[tuple[float, RiskLevel]]) -> RouteRisk:
    """Summarize (mile, level) checkpoints, ordered by mile."""
    if not checkpoints:
        raise ValueError("No checkpoints to summarize")

    miles_by_level = dict.fromkeys(RiskLevel, 0.0)
    weighted = 0.0
    for (m0, l0), (m1, l1) in itertools.pairwise(checkpoints):
        level = max(l0, l1)
        miles_by_level[level] += m1 - m0
        weighted += (m1 - m0) * level

    total = sum(miles_by_level.values())
    max_level = max(level for _, level in checkpoints)
    average = weighted / total if total > 0 else float(max_level)
    return RouteRisk(miles_by_level=miles_by_level, average_risk=average, max_level=max_level)


def ranking_key(candidate: RouteCandidate) -> tuple[float, float, float, float, float]:
    # Rounded so float noise doesn't decide a tie that should fall through to the next rule.
    risk = candidate.risk
    return (
        round(risk.miles(RiskLevel.NO_TRAVEL), 1),
        round(risk.miles(RiskLevel.SEVERE), 1),
        round(risk.miles(RiskLevel.HIGH), 1),
        round(risk.average_risk, 3),
        candidate.duration_s,
    )


def rank(candidates: list[RouteCandidate]) -> list[int]:
    """Candidate indices, best first."""
    return sorted(range(len(candidates)), key=lambda i: ranking_key(candidates[i]))


_CRITERIA = (
    "fewer No Travel miles",
    "fewer Severe miles",
    "fewer High miles",
    "lower average risk",
    "shorter travel time",
)


def explain(best: RouteCandidate, runner_up: RouteCandidate | None) -> str:
    """Why `best` beat `runner_up`: the first ranking criterion where they differ."""
    if runner_up is None:
        return "Only route available."
    for criterion, a, b in zip(_CRITERIA, ranking_key(best), ranking_key(runner_up), strict=True):
        if a != b:
            return f"Recommended: {criterion} than the next best route."
    return "Recommended: tied with the next best route on every criterion."
