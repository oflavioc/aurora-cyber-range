# Gerado por tools/codegen.py. Nao editar a mao.
# Fonte canonica: contracts/events.schema.yaml

from typing import Final

ASSESSMENT_SUBMITTED: Final[str] = "assessment_submitted"
ATTACK_STAGE_REACHED: Final[str] = "attack_stage_reached"
AUDIT_QUERY_PERFORMED: Final[str] = "audit_query_performed"
BARS_SCORE_SUBMITTED: Final[str] = "bars_score_submitted"
BRANCH_SELECTED: Final[str] = "branch_selected"
CAPABILITY_GAP_DECLARED: Final[str] = "capability_gap_declared"
CLASSIFICATION_DECLARED: Final[str] = "classification_declared"
COMMUNICATION_SUBMITTED: Final[str] = "communication_submitted"
CONTAINMENT_DECLARED: Final[str] = "containment_declared"
CONTINUITY_ACTION_TAKEN: Final[str] = "continuity_action_taken"
DECISION_MADE: Final[str] = "decision_made"
EVIDENCE_SOURCE_ACCESSED: Final[str] = "evidence_source_accessed"
EVIDENCE_SOURCE_OPENED: Final[str] = "evidence_source_opened"
EVIDENCE_SOURCE_RELEASED: Final[str] = "evidence_source_released"
EXERCISE_PAUSED: Final[str] = "exercise_paused"
EXERCISE_RESET: Final[str] = "exercise_reset"
EXERCISE_RESUMED: Final[str] = "exercise_resumed"
EXERCISE_STARTED: Final[str] = "exercise_started"
FACT_MATERIALIZED: Final[str] = "fact_materialized"
IDENTITY_SCOPE_DISABLED: Final[str] = "identity_scope_disabled"
INCIDENT_DECLARED: Final[str] = "incident_declared"
INJECT_FIRED: Final[str] = "inject_fired"
INJECT_VIEWED: Final[str] = "inject_viewed"
INTEGRITY_VALIDATION_DECLARED: Final[str] = "integrity_validation_declared"
OBSERVED_MARKER_SET: Final[str] = "observed_marker_set"
QUALITATIVE_NOTE_ADDED: Final[str] = "qualitative_note_added"
REGULATORY_NOTICE_SUBMITTED: Final[str] = "regulatory_notice_submitted"
ROLLBACK_PERFORMED: Final[str] = "rollback_performed"
SEPARATE_INCIDENT_DECLARED: Final[str] = "separate_incident_declared"
SERVICE_RESTORATION_DECLARED: Final[str] = "service_restoration_declared"
TELEMETRY_EMITTED: Final[str] = "telemetry_emitted"
VERIFICATION_PREDICATE_SATISFIED: Final[str] = "verification_predicate_satisfied"
VPN_ACCESS_REVOKED: Final[str] = "vpn_access_revoked"

ALL_EVENT_TYPES: Final[tuple[str, ...]] = (
    ASSESSMENT_SUBMITTED,
    ATTACK_STAGE_REACHED,
    AUDIT_QUERY_PERFORMED,
    BARS_SCORE_SUBMITTED,
    BRANCH_SELECTED,
    CAPABILITY_GAP_DECLARED,
    CLASSIFICATION_DECLARED,
    COMMUNICATION_SUBMITTED,
    CONTAINMENT_DECLARED,
    CONTINUITY_ACTION_TAKEN,
    DECISION_MADE,
    EVIDENCE_SOURCE_ACCESSED,
    EVIDENCE_SOURCE_OPENED,
    EVIDENCE_SOURCE_RELEASED,
    EXERCISE_PAUSED,
    EXERCISE_RESET,
    EXERCISE_RESUMED,
    EXERCISE_STARTED,
    FACT_MATERIALIZED,
    IDENTITY_SCOPE_DISABLED,
    INCIDENT_DECLARED,
    INJECT_FIRED,
    INJECT_VIEWED,
    INTEGRITY_VALIDATION_DECLARED,
    OBSERVED_MARKER_SET,
    QUALITATIVE_NOTE_ADDED,
    REGULATORY_NOTICE_SUBMITTED,
    ROLLBACK_PERFORMED,
    SEPARATE_INCIDENT_DECLARED,
    SERVICE_RESTORATION_DECLARED,
    TELEMETRY_EMITTED,
    VERIFICATION_PREDICATE_SATISFIED,
    VPN_ACCESS_REVOKED,
)
