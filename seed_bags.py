from database import SessionLocal
import models
from datetime import datetime

db = SessionLocal()

# počisti
db.query(models.Bag).delete()
db.commit()

partners = db.query(models.Partner).order_by(models.Partner.id.asc()).all()
if not partners:
    raise Exception("⚠️ Nema partnera! Prvo pokreni seed_partners.py")

now = datetime.utcnow()

bags = [
    models.Bag(
        naziv="Pekarska kesa iznenađenja",
        opis="Miks peciva i hlebova koji su ostali od dana.",
        cena=3.5,
        kolicina=5,
        vreme_preuzimanja=now.replace(hour=18, minute=0, second=0, microsecond=0),
        status="active",
        partner_id=partners[0].id,
        adresa="Glavna 12, Beograd",
        lat=None,  # koristiće partner.lat/lng kao fallback
        lng=None,
    ),
    models.Bag(
        naziv="Dnevni meni iznenađenja",
        opis="Topla jela po izboru kuvara.",
        cena=5.0,
        kolicina=3,
        vreme_preuzimanja=now.replace(hour=20, minute=0, second=0, microsecond=0),
        status="active",
        partner_id=partners[min(1, len(partners)-1)].id,
        adresa="Trg Republike 5, Novi Sad",
        lat=None,
        lng=None,
    ),
    models.Bag(
        naziv="Kafa i kolač",
        opis="Kafa + kolač dana po izboru osoblja.",
        cena=2.5,
        kolicina=4,
        vreme_preuzimanja=now.replace(hour=17, minute=0, second=0, microsecond=0),
        status="active",
        partner_id=partners[min(2, len(partners)-1)].id,
        adresa="Bulevar Kralja Aleksandra 45, Beograd",
        lat=None,
        lng=None,
    ),
]

db.add_all(bags)
db.commit()

print("✅ Seed: Bagovi dodati.")
db.close()
