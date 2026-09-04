"""Council profiles: which models deliberate, how they judge, what comes out.

A profile is the single knob that trades cost/latency against depth. Pick one
per question type instead of editing config.py.
"""

from dataclasses import dataclass
from typing import Dict, List

from .config import COUNCIL_MODELS, CHAIRMAN_MODEL


@dataclass(frozen=True)
class Profile:
    """One council configuration."""

    name: str
    description: str
    models: List[str]
    chairman: str
    rubric: str
    output_schema: str
    max_context_chars: int = 60000
    peer_review: bool = True

    @property
    def expected_calls(self) -> int:
        return len(self.models) * (2 if self.peer_review else 1) + 1

    @property
    def expected_latency(self) -> str:
        return "~90-180s" if self.peer_review else "~20-40s"


_DECISION_RUBRIC = """Judge every response against these criteria, in this order of weight:
1. Correctness — factually right, no invented APIs, constraints or numbers.
2. Trade-off honesty — names the real downsides of its own recommendation instead of selling one option.
3. Actionability — usable in the concrete context given, not generic advice.
4. Risk awareness — names failure modes, reversibility and what would have to be true.
Penalise: length without substance, hedging that avoids a recommendation, restating the question."""

_RESEARCH_RUBRIC = """Judge every response against these criteria, in this order of weight:
1. Coverage — spans the relevant option/answer space instead of one obvious branch.
2. Specificity and evidence — concrete names, mechanisms, numbers; verifiable claims over vibes.
3. Calibration — distinguishes established fact from inference and says what is uncertain.
4. Structure — the reader can act on it.
Penalise: overclaiming, filler, confident answers to genuinely open questions."""

_DECISION_SCHEMA = """Structure your answer with exactly these sections:

## Empfehlung
One concrete recommendation, stated in the first two sentences. No hedging.

## Begruendung
Why this one wins, tied to the context given.

## Alternativen & Trade-offs
The 2-3 serious alternatives and what each costs.

## Dissens im Konzil
Where the council members actually disagreed and what that disagreement is about. If they agreed on everything, say so explicitly and note what that might mean (shared blind spot vs. genuinely easy call).

## Risiken
What can go wrong, how reversible the recommendation is.

## Naechste Schritte
Concrete next actions."""

_RESEARCH_SCHEMA = """Structure your answer with exactly these sections:

## Kurzfassung
5-8 lines answering the question directly.

## Befunde
The substance, in structured bullets.

## Konsens
What all council members agreed on.

## Dissens & Unsicherheiten
Where they disagreed, and where the evidence is genuinely thin.

## Offene Fragen
What would need to be checked to firm this up."""

_QUICK_SCHEMA = """Structure your answer with exactly these sections:

## Kurzfassung
5-8 lines answering the question directly.

## Details
The substance, in structured bullets."""


PROFILES: Dict[str, Profile] = {
    "quick": Profile(
        name="quick",
        description=(
            "Cost escape hatch: 2 models, no peer review, direct synthesis. "
            "Use when you want a second opinion, not a deliberation."
        ),
        models=COUNCIL_MODELS[:2],
        chairman=CHAIRMAN_MODEL,
        rubric="",
        output_schema=_QUICK_SCHEMA,
        max_context_chars=40000,
        peer_review=False,
    ),
    "decision": Profile(
        name="decision",
        description=(
            "Full council for technical/architecture decisions that are "
            "expensive to reverse and have no cheap ground truth."
        ),
        models=list(COUNCIL_MODELS),
        chairman=CHAIRMAN_MODEL,
        rubric=_DECISION_RUBRIC,
        output_schema=_DECISION_SCHEMA,
        max_context_chars=60000,
    ),
    "research": Profile(
        name="research",
        description=(
            "Full council for open questions where model diversity buys "
            "coverage rather than a verdict."
        ),
        models=list(COUNCIL_MODELS),
        chairman=CHAIRMAN_MODEL,
        rubric=_RESEARCH_RUBRIC,
        output_schema=_RESEARCH_SCHEMA,
        max_context_chars=60000,
    ),
}

DEFAULT_PROFILE = "decision"


def get_profile(name: str) -> Profile:
    """Look up a profile by name, with a helpful error on typos."""
    try:
        return PROFILES[name]
    except KeyError:
        raise ValueError(
            f"Unknown profile '{name}'. Available: {', '.join(PROFILES)}"
        ) from None
