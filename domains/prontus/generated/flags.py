# Gerado por tools/codegen.py. Nao editar a mao.
# Fonte canonica: domains/prontus/flags.yaml

from typing import Final

PRONTUS_ADMISSION_OFFLINE: Final[str] = "prontus.admission_offline"
PRONTUS_RECORD_INTEGRITY_SUSPECT: Final[str] = "prontus.record_integrity_suspect"

ALL_FLAGS: Final[tuple[str, ...]] = (
    PRONTUS_ADMISSION_OFFLINE,
    PRONTUS_RECORD_INTEGRITY_SUSPECT,
)
