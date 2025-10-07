from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.domain import Report, TrustedContact


class TrustedContactService:
    """Gestiona la selección de contactos de confianza por dominio."""

    @staticmethod
    def get_active_contact(db: Session, domain_id: int) -> Optional[TrustedContact]:
        return (
            db.query(TrustedContact)
            .filter(TrustedContact.domain_id == domain_id, TrustedContact.is_active == True)
            .order_by(TrustedContact.updated_at.desc(), TrustedContact.created_at.desc())
            .first()
        )

    @staticmethod
    def get_contact_options(report: Report) -> Dict[str, List[str]]:
        site_data = report.get_json_data("site_data") or {}
        contacts = site_data.get("contacts", {})

        emails = sorted({c.strip() for c in contacts.get("emails", []) if c and c.strip()})
        phones = sorted({c.strip() for c in contacts.get("phones", []) if c and c.strip()})

        return {"emails": emails, "phones": phones}

    @staticmethod
    def set_trusted_contact(
        db: Session,
        *,
        domain_id: int,
        report_id: Optional[int],
        email: Optional[str],
        phone: Optional[str],
    ) -> Optional[TrustedContact]:
        email = email.strip() if email else None
        phone = phone.strip() if phone else None

        existing = TrustedContactService.get_active_contact(db, domain_id)

        if not email and not phone:
            if existing:
                existing.is_active = False
                existing.email = None
                existing.phone = None
                existing.report_id = report_id
                existing.updated_at = datetime.utcnow()
                db.commit()
                db.refresh(existing)
            return None

        if existing:
            existing.email = email
            existing.phone = phone
            existing.report_id = report_id
            existing.is_active = True
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing

        trusted_contact = TrustedContact(
            domain_id=domain_id,
            report_id=report_id,
            email=email,
            phone=phone,
            is_active=True,
        )
        db.add(trusted_contact)
        db.commit()
        db.refresh(trusted_contact)
        return trusted_contact

    @staticmethod
    def serialize(contact: Optional[TrustedContact]) -> Optional[Dict[str, Optional[str]]]:
        if not contact or not contact.is_active:
            return None
        return {
            "id": contact.id,
            "domain_id": contact.domain_id,
            "report_id": contact.report_id,
            "email": contact.email,
            "phone": contact.phone,
            "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
        }
