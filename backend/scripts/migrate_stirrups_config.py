from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.schemas.design import StirrupConfig  # noqa: E402


def convert_stirrups_payload(stirrups_payload: list[dict]) -> tuple[list[dict], bool]:
    """Normaliza cada configuración según StirrupConfig."""
    converted: list[dict] = []
    changed = False

    for entry in stirrups_payload:
        validated = StirrupConfig.model_validate(entry)
        converted_entry = validated.model_dump()
        converted.append(converted_entry)
        if entry != converted_entry:
            changed = True

    return converted, changed


def migrate() -> None:
    session: Session = SessionLocal()
    updated_records = 0

    try:
        records = session.query(models.DespieceViga).all()
        for record in records:
            payload = record.stirrups_config or []
            if not payload:
                continue

            converted, changed = convert_stirrups_payload(payload)
            if not changed:
                continue

            record.stirrups_config = converted
            updated_records += 1

        if updated_records:
            session.commit()
        else:
            session.rollback()
    finally:
        session.close()

    print(f"Registros actualizados: {updated_records}")


if __name__ == "__main__":
    migrate()
