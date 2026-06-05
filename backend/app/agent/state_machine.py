"""Lead state machine — defines valid transitions."""
from enum import Enum


class LeadState(str, Enum):
    NEW = "new"
    ENRICHED = "enriched"
    CONTACTED = "contacted"
    ENGAGED = "engaged"          # opened or clicked
    REPLIED = "replied"
    CONVERTED = "converted"
    COLD = "cold"                # no engagement after N days
    UNSUBSCRIBED = "unsubscribed"
    CLOSED = "closed"


VALID_TRANSITIONS: dict[str, set[str]] = {
    LeadState.NEW: {LeadState.ENRICHED, LeadState.CLOSED, LeadState.UNSUBSCRIBED},
    LeadState.ENRICHED: {LeadState.CONTACTED, LeadState.CLOSED, LeadState.UNSUBSCRIBED},
    LeadState.CONTACTED: {LeadState.ENGAGED, LeadState.REPLIED, LeadState.COLD, LeadState.UNSUBSCRIBED, LeadState.CLOSED},
    LeadState.ENGAGED: {LeadState.REPLIED, LeadState.COLD, LeadState.CONVERTED, LeadState.UNSUBSCRIBED, LeadState.CLOSED, LeadState.CONTACTED},
    LeadState.REPLIED: {LeadState.CONVERTED, LeadState.CLOSED, LeadState.UNSUBSCRIBED, LeadState.ENGAGED},
    LeadState.COLD: {LeadState.CLOSED, LeadState.ENGAGED, LeadState.CONTACTED, LeadState.UNSUBSCRIBED},
    LeadState.CONVERTED: {LeadState.CLOSED},
    LeadState.UNSUBSCRIBED: set(),
    LeadState.CLOSED: set(),
}


def can_transition(from_state: str, to_state: str) -> bool:
    """Check if a state transition is allowed."""
    if from_state == to_state:
        return True
    valid = VALID_TRANSITIONS.get(from_state, set())
    return to_state in valid
