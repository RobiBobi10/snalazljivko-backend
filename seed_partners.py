import os
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from database import SessionLocal
import models

# Konfig preko env (po defaultu NE briše)
USERNAME = os.getenv("SEED_PARTNER_USERNAME", "partner")
EMAIL = os.getenv("SEED_PARTNER_EMAIL", "partner@example.com")
PASSWORD = os.getenv("SEED_PARTNER_PASSWORD", "tajna")
DO_RESET = os.getenv("SEED_RESET", "0") == "1"  # privremeni reset (DROP demo podataka)

def _hash_password(raw: str) -> str:
    import hashlib
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def upsert_partner(db: Session, *, naziv, login_username=None, email=None, adresa=None, lat=None, lng=None, thumbnail_url=None, with_login=False):
    q = db.query(models.Partner).filter(models.Partner.naziv == naziv)
    p = q.first()
    if not p:
        p = models.Partner(naziv=naziv)
        db.add(p)
        db.flush()
    # ažuriranja
    if with_login:
        p.login_username = login_username or naziv.lower().replace(" ", "")
        p.email = email or f"{p.login_username}@example.com"
        p.password_hash = _hash_password(PASSWORD)
        p.is_active = True
    if adresa is not None: p.adresa = adresa
    if lat is not None: p.lat = lat
    if lng is not None: p.lng = lng
    if thumbnail_url is not None: p.thumbnail_url = thumbnail_url
    return p

def upsert_bag(db: Session, *, partner_id, naziv, opis=None, cena=0.0, kolicina=1, status="active",
               adresa=None, lat=None, lng=None, vreme_preuzimanja=None, thumbnail_url=None):
    r = db.query(models.Bag).filter(
        and_(models.Bag.partner_id == partner_id, models.Bag.naziv == naziv)
    ).first()
    if not r:
        r = models.Bag(
            partner_id=partner_id,
            naziv=naziv,
            created_at=datetime.utcnow(),
        )
        db.add(r)
        db.flush()
    # ažuriranja
    r.opis = opis
    r.cena = float(cena)
    r.kolicina = int(kolicina)
    r.status = status
    r.adresa = adresa
    r.lat = lat
    r.lng = lng
    r.vreme_preuzimanja = vreme_preuzimanja
    r.thumbnail_url = thumbnail_url
    return r

def main():
    db: Session = SessionLocal()
    try:
        # (opciono) reset demo podataka
        if DO_RESET:
            # brišemo samo kese; partnere ostavljamo (lakši login)
            db.query(models.Bag).delete()
            db.commit()
            print("↺ Reset: obrisane su sve kese (partners ostaju).")

        # Glavni login partner
        core = upsert_partner(
            db,
            naziv=USERNAME,
            login_username=USERNAME,
            email=EMAIL,
            adresa="Test adresa 1",
            lat=44.8125, lng=20.4612,
            thumbnail_url=None,
            with_login=True,
        )

        # Dodatni partneri
        starbucks = upsert_partner(
            db,
            naziv="Starbucks Antwerp",
            adresa="Antwerpen, Belgija",
            lat=51.2194, lng=4.4025,
            thumbnail_url="https://upload.wikimedia.org/wikipedia/commons/d/d3/Starbucks_Corporation_Logo_2011.svg",
            with_login=False,
        )
        pekara = upsert_partner(
            db,
            naziv="Pekara Bruxelles",
            adresa="Bruxelles, Belgija",
            lat=50.8503, lng=4.3517,
            thumbnail_url=None,
            with_login=False,
        )
        pizzeria = upsert_partner(
            db,
            naziv="Pizzeria Roma",
            adresa="Bruxelles, Belgija",
            lat=50.8485, lng=4.3521,
            thumbnail_url=None,
            with_login=False,
        )

        db.commit()

        # Kese za core partnera
        upsert_bag(
            db, partner_id=core.id, naziv="Demo kesa", opis="Mix peciva",
            cena=4.00, kolicina=3, status="active",
            adresa="Test ulica 2", lat=44.8125, lng=20.4612,
            vreme_preuzimanja=None, thumbnail_url=core.thumbnail_url
        )

        # Kese za Starbucks
        upsert_bag(
            db, partner_id=starbucks.id, naziv="Surprise Bag Kafa & Peciva",
            opis="Mix peciva i kafa pred kraj dana", cena=4.99, kolicina=3,
            status="active", adresa="Antwerpen Centar", lat=51.221, lng=4.399,
            vreme_preuzimanja=datetime.utcnow() + timedelta(hours=3),
            thumbnail_url=starbucks.thumbnail_url
        )
        upsert_bag(
            db, partner_id=starbucks.id, naziv="Kafa To Go",
            opis="Velika kafa sa mlekom", cena=2.50, kolicina=5,
            status="active", adresa="Antwerpen Centar", lat=51.221, lng=4.399,
            vreme_preuzimanja=None, thumbnail_url=starbucks.thumbnail_url
        )

        # Kese za Pekaru
        upsert_bag(
            db, partner_id=pekara.id, naziv="Pekara Mix",
            opis="Mix hlebova i peciva", cena=3.50, kolicina=5,
            status="active", adresa="Bruxelles Centar", lat=50.849, lng=4.352,
            vreme_preuzimanja=datetime.utcnow() + timedelta(hours=2),
            thumbnail_url=pekara.thumbnail_url
        )

        # Kese za Pizzeriu
        upsert_bag(
            db, partner_id=pizzeria.id, naziv="Pizza Surprise",
            opis="2 kriške pizze", cena=4.00, kolicina=2,
            status="active", adresa="Bruxelles Centar", lat=50.8485, lng=4.3521,
            vreme_preuzimanja=None, thumbnail_url=pizzeria.thumbnail_url
        )

        db.commit()
        print("✔ Seeding završen (idempotentno).")
        print("   Savet: za privremeno čišćenje kesa pokreni sa SEED_RESET=1")
    finally:
        db.close()

if __name__ == "__main__":
    main()
