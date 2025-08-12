from sqlalchemy.orm import Session
from typing import List, Optional
import models, schemas

# ================
# PARTNERS
# ================
def get_partners(db: Session) -> List[models.Partner]:
    return db.query(models.Partner).all()

def get_partner_by_id(db: Session, partner_id: int) -> Optional[models.Partner]:
    return db.query(models.Partner).filter(models.Partner.id == partner_id).first()

def create_partner(db: Session, partner: schemas.PartnerCreate) -> models.Partner:
    db_partner = models.Partner(
        naziv=partner.naziv,
        adresa=partner.adresa,
        lat=partner.lat,
        lng=partner.lng,
    )
    db.add(db_partner)
    db.commit()
    db.refresh(db_partner)
    return db_partner

# ================
# BAGS
# ================
def get_bags(db: Session) -> List[models.Bag]:
    return db.query(models.Bag).all()

def get_bag_by_id(db: Session, bag_id: int) -> Optional[models.Bag]:
    return db.query(models.Bag).filter(models.Bag.id == bag_id).first()

def create_bag(db: Session, bag: schemas.BagCreate) -> models.Bag:
    db_bag = models.Bag(
        naziv=bag.naziv,
        opis=bag.opis,
        cena=bag.cena,
        kolicina=bag.kolicina,
        vreme_preuzimanja=bag.vreme_preuzimanja,
        status=bag.status,
        partner_id=bag.partner_id,
        adresa=bag.adresa,
        lat=bag.lat,
        lng=bag.lng,
    )
    db.add(db_bag)
    db.commit()
    db.refresh(db_bag)
    return db_bag

def update_bag(db: Session, bag_id: int, patch: schemas.BagUpdate) -> Optional[models.Bag]:
    db_bag = db.query(models.Bag).filter(models.Bag.id == bag_id).first()
    if not db_bag:
        return None
    for key, value in patch.dict(exclude_unset=True).items():
        setattr(db_bag, key, value)
    db.commit()
    db.refresh(db_bag)
    return db_bag

def delete_bag(db: Session, bag_id: int) -> bool:
    db_bag = db.query(models.Bag).filter(models.Bag.id == bag_id).first()
    if not db_bag:
        return False
    db.delete(db_bag)
    db.commit()
    return True
