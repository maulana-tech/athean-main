"""Response models surfaced by the FastAPI gateway.

These are thin wrappers around the canonical ``athean_core.schema``
types — they exist so the gateway can shape responses for the web
dashboard without exposing every internal field.
"""

from athean_api.schemas.agent import AgentSummary
from athean_api.schemas.counterfactual import CounterfactualSummary
from athean_api.schemas.debate import DebateEnvelope
from athean_api.schemas.goal import GoalSummary
from athean_api.schemas.passport import PassportSummary
from athean_api.schemas.restraint import RestraintSummary
from athean_api.schemas.signal import SignalSummary
from athean_api.schemas.thesis import ThesisSummary
from athean_api.schemas.trace import TraceEventSummary
from athean_api.schemas.trade import TradeSummary

__all__ = [
    "AgentSummary",
    "CounterfactualSummary",
    "DebateEnvelope",
    "GoalSummary",
    "PassportSummary",
    "RestraintSummary",
    "SignalSummary",
    "ThesisSummary",
    "TraceEventSummary",
    "TradeSummary",
]
