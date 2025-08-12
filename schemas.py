from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# =================
# PARTNER
# =================
class PartnerBase(BaseModel):
    naziv: str
    adresa: Optional[str] = None
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    thumbnail_url: Optional[str] = None

class PartnerCreate(PartnerBase):
    pass

class Partner(PartnerBase):
    id: int
    email: Optional[str] = None
    login_username: Optional[str] = None
    is_active: Optional[bool] = True

    class Config:
        from_attributes = True

# =================
# BAG
# =================
class BagBase(BaseModel):
    naziv: str
    opis: Optional[str] = None
    cena: float
    kolicina: int
    vreme_preuzimanja: Optional[datetime] = None
    status: str = "active"
    partner_id: int
    adresa: Optional[str] = None
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    thumbnail_url: Optional[str] = None

class BagCreate(BagBase):
    pass

class BagUpdate(BaseModel):
    naziv: Optional[str] = None
    opis: Optional[str] = None
    cena: Optional[float] = None
    kolicina: Optional[int] = None
    vreme_preuzimanja: Optional[datetime] = None
    status: Optional[str] = None
    partner_id: Optional[int] = None
    adresa: Optional[str] = None
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    thumbnail_url: Optional[str] = None

class Bag(BagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# =================
# PAGINATION + STATS + AUTH
# =================
class PaginatedBags(BaseModel):
    items: List[Bag]
    total: int
    page: int
    size: int
    pages: int

class Stats(BaseModel):
    broj_bagova: int
    broj_porudzbina: int
    ukupna_zarada: float

class Token(BaseModel):
    access_token: str
    token_type: str

# Sprint 8 — Auth DTOs
class LoginBody(BaseModel):
    email_or_username: str
    password: str
    role: Optional[str] = None  # "partner" | "customer" | None

class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
