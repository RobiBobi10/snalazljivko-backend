from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Partner(Base):
    __tablename__ = "partners"

    id = Column(Integer, primary_key=True, index=True)
    naziv = Column(String, nullable=False)
    adresa = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    # Sprint 6
    thumbnail_url = Column(String, nullable=True)

    # Sprint 8 — auth (poravnato sa 20250811_0003_auth_roles.py)
    email = Column(String, nullable=True)
    login_username = Column(String, nullable=True, index=True)
    password_hash = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    bags = relationship("Bag", back_populates="partner", cascade="all, delete-orphan")

class Bag(Base):
    __tablename__ = "bags"

    id = Column(Integer, primary_key=True, index=True)
    naziv = Column(String, nullable=False)
    opis = Column(String, nullable=True)
    cena = Column(Float, nullable=False)
    kolicina = Column(Integer, nullable=False, default=1)
    vreme_preuzimanja = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="active")

    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=False)
    partner = relationship("Partner", back_populates="bags")

    adresa = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    # Sprint 6
    thumbnail_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

# Sprint 8 — kupac (poravnato sa 20250811_0003_auth_roles.py)
class User(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, index=True)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
