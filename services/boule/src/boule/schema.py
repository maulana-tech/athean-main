"""Backwards-compatible re-export from `athean_core.schema`.

Boule originally defined the canonical schemas; they have since moved to
``athean_core`` so every service can depend on them without dragging in
Boule itself. Keep importing from ``boule.schema`` is fine — this module is
a thin pass-through and adds no behaviour.
"""

from athean_core.schema import (
    AgentVote,
    ApprovalToken,
    ExitConditions,
    ExitSignal,
    RejectionRecord,
    Signal,
    Thesis,
    ThesisBlock,
    Trade,
    TraceEvent,
    utc_now,
)

__all__ = [
    "AgentVote",
    "ApprovalToken",
    "ExitConditions",
    "ExitSignal",
    "RejectionRecord",
    "Signal",
    "Thesis",
    "ThesisBlock",
    "Trade",
    "TraceEvent",
    "utc_now",
]
