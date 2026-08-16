# Gerado por tools/codegen.py. Nao editar a mao.
# Fonte canonica: domains/academus/flags.yaml

from typing import Final

ACADEMUS_ANPD_NOTIFICATION_WINDOW_OPEN: Final[str] = "academus.anpd_notification_window_open"
ACADEMUS_ENROLLMENT_OFFLINE: Final[str] = "academus.enrollment_offline"
ACADEMUS_ENROLLMENT_SERVICE_STATE: Final[str] = "academus.enrollment_service_state"
ACADEMUS_FEDERATED_SESSION_ACTIVE: Final[str] = "academus.federated_session_active"
ACADEMUS_GRADE_INTEGRITY_SUSPECT: Final[str] = "academus.grade_integrity_suspect"
ACADEMUS_GRADES_READONLY: Final[str] = "academus.grades_readonly"
ACADEMUS_LMS_DEGRADED: Final[str] = "academus.lms_degraded"
ACADEMUS_LMS_SESSION_DROP_RATE: Final[str] = "academus.lms_session_drop_rate"
ACADEMUS_PORTAL_DEFACED: Final[str] = "academus.portal_defaced"
ACADEMUS_RESEARCH_DATA_EXPOSED: Final[str] = "academus.research_data_exposed"
ACADEMUS_STUDENT_DATA_EXPOSED: Final[str] = "academus.student_data_exposed"
ACADEMUS_TRANSCRIPT_ISSUANCE_BLOCKED: Final[str] = "academus.transcript_issuance_blocked"
ACADEMUS_VPN_MFA_ENFORCED: Final[str] = "academus.vpn_mfa_enforced"

ALL_FLAGS: Final[tuple[str, ...]] = (
    ACADEMUS_ANPD_NOTIFICATION_WINDOW_OPEN,
    ACADEMUS_ENROLLMENT_OFFLINE,
    ACADEMUS_ENROLLMENT_SERVICE_STATE,
    ACADEMUS_FEDERATED_SESSION_ACTIVE,
    ACADEMUS_GRADE_INTEGRITY_SUSPECT,
    ACADEMUS_GRADES_READONLY,
    ACADEMUS_LMS_DEGRADED,
    ACADEMUS_LMS_SESSION_DROP_RATE,
    ACADEMUS_PORTAL_DEFACED,
    ACADEMUS_RESEARCH_DATA_EXPOSED,
    ACADEMUS_STUDENT_DATA_EXPOSED,
    ACADEMUS_TRANSCRIPT_ISSUANCE_BLOCKED,
    ACADEMUS_VPN_MFA_ENFORCED,
)
