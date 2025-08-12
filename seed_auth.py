# seed_auth.py
import os
import hashlib
from sqlalchemy.orm import Session
from database import SessionLocal
import models

USERNAME = os.getenv("SEED_PARTNER_USERNAME", "partner")
EMAIL = os.getenv("SEED_PARTNER_EMAIL", "partner@example.com")
PASSWORD = os.getenv("SEED_PARTNER_PASSWORD", "tajna")

def _hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def main():
    db: Session = SessionLocal()
    try:
        # Pronađi partnera po login_username ili nazivu
        partner = (
            db.query(models.Partner)
            .filter(
                (models.Partner.login_username == USERNAME) |
                (models.Partner.naziv == USERNAME)
            )
            .first()
        )
        if not partner:
            # Ako nema, kreiraj osnovnog partnera
            partner = models.Partner(
                naziv=USERNAME,
                login_username=USERNAME,
                email=EMAIL,
                password_hash=_hash_password(PASSWORD),
                is_active=True,
            )
            db.add(partner)
            db.commit()
            db.refresh(partner)
            print(f"✔ Kreiran partner '{USERNAME}' sa lozinkom '{PASSWORD}'. (email: {EMAIL})")
        else:
            # Updejtuj kredencijale ako fale
            changed = False
            if not partner.login_username:
                partner.login_username = USERNAME
                changed = True
            if not partner.email:
                partner.email = EMAIL
                changed = True
            partner.password_hash = _hash_password(PASSWORD)
            partner.is_active = True
            if changed:
                print("ℹ Ažuriram login_username/email.")
            db.commit()
            print(f"✔ Partner '{USERNAME}' spreman za login. Lozinka resetovana na '{PASSWORD}'.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
