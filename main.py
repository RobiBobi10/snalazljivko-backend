# main.py
from datetime import datetime, timedelta
from typing import Optional, List, Any, Dict
import os
import io
import csv
import hashlib
import uuid

from fastapi import FastAPI, Depends, HTTPException, status, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from sqlalchemy import func, asc, desc, or_

import models, schemas
from database import SessionLocal

# -----------------------------------------------------------------------------
# App & CORS
# -----------------------------------------------------------------------------
app = FastAPI(title="Snalazljivko API")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static za upload
STATIC_DIR = os.path.join(os.getcwd(), "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Javna baza URL-a backend-a (za generisanje apsolutnih linkova na slike)
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")

# -----------------------------------------------------------------------------
# Auth / JWT helpers (role-aware)
# -----------------------------------------------------------------------------
SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7d

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # legacy compatibility

def _hash_password(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _verify_password(raw: str, hashed: str) -> bool:
    return _hash_password(raw) == hashed

def create_access_token(data: Dict[str, Any], expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Model refs
PartnerModel = getattr(models, "Partner", None)
BagModel = getattr(models, "Bag", None)
UserModel = getattr(models, "User", None)
HAS_USER = UserModel is not None

# -----------------------------------------------------------------------------
# Current user dependency (role-aware)
# -----------------------------------------------------------------------------
def get_current_identity(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Dict[str, Any]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nevažeći token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub: str = payload.get("sub")
        role: str = payload.get("role", "partner")
        if sub is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    identity = {"role": role, "id": None, "email": None}
    if role == "partner" and PartnerModel is not None:
        partner = db.query(PartnerModel).filter(
            (PartnerModel.email == sub) | (PartnerModel.login_username == sub) | (PartnerModel.naziv == sub)
        ).first()
        if not partner:
            raise credentials_exception
        identity.update({"id": partner.id, "email": getattr(partner, "email", None)})
    elif role == "customer" and HAS_USER:
        user = db.query(UserModel).filter(UserModel.email == sub).first()
        if not user:
            raise credentials_exception
        identity.update({"id": user.id, "email": user.email})
    else:
        raise credentials_exception
    return identity

# -----------------------------------------------------------------------------
# Legacy partner login (/token) — kompatibilnost sa frontendom
# -----------------------------------------------------------------------------
from fastapi import Body
from pydantic import BaseModel, EmailStr

@app.post("/token")
def legacy_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if PartnerModel is None:
        raise HTTPException(status_code=500, detail="Partner model nije dostupan.")
    username = form_data.username.strip()
    password = form_data.password
    partner = db.query(PartnerModel).filter(
        (PartnerModel.email == username) | (PartnerModel.login_username == username) | (PartnerModel.naziv == username)
    ).first()
    if not partner or not partner.is_active:
        raise HTTPException(status_code=400, detail="Pogrešan username/email ili lozinka.")
    stored = getattr(partner, "password_hash", None)
    if stored is None:
        if getattr(partner, "password", None) != password:
            raise HTTPException(status_code=400, detail="Pogrešan username/email ili lozinka.")
    else:
        if not _verify_password(password, stored):
            raise HTTPException(status_code=400, detail="Pogrešan username/email ili lozinka.")

    token = create_access_token({"sub": partner.login_username or partner.email or partner.naziv, "role": "partner"})
    return {"access_token": token, "token_type": "bearer", "role": "partner"}

# -----------------------------------------------------------------------------
# New Auth API
# -----------------------------------------------------------------------------
class LoginBody(BaseModel):
    email_or_username: str
    password: str
    role: Optional[str] = None  # "partner" | "customer" | None

class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

@app.post("/auth/login")
def auth_login(body: LoginBody, db: Session = Depends(get_db)):
    identifier = body.email_or_username.strip()
    if body.role in (None, "partner"):
        partner = None
        if PartnerModel is not None:
            partner = db.query(PartnerModel).filter(
                (PartnerModel.email == identifier) | (PartnerModel.login_username == identifier) | (PartnerModel.naziv == identifier)
            ).first()
            if partner and partner.is_active:
                stored = getattr(partner, "password_hash", None)
                ok = (_verify_password(body.password, stored) if stored else getattr(partner, "password", None) == body.password)
                if ok:
                    token = create_access_token({"sub": partner.login_username or partner.email or partner.naziv, "role": "partner"})
                    return {"access_token": token, "token_type": "bearer", "role": "partner"}
        if body.role == "partner":
            raise HTTPException(status_code=400, detail="Pogrešan email/username ili lozinka.")
    if body.role in (None, "customer"):
        if not HAS_USER:
            raise HTTPException(status_code=501, detail="Registracija/login kupaca još nije omogućena (potrebna migracija).")
        user = db.query(UserModel).filter(UserModel.email == identifier).first()
        if not user or not user.is_active:
            raise HTTPException(status_code=400, detail="Pogrešan email ili lozinka.")
        if not _verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=400, detail="Pogrešan email ili lozinka.")
        token = create_access_token({"sub": user.email, "role": "customer"})
        return {"access_token": token, "token_type": "bearer", "role": "customer"}
    raise HTTPException(status_code=400, detail="Neispravni kredencijali.")

@app.post("/auth/register")
def auth_register(body: RegisterBody, db: Session = Depends(get_db)):
    if not HAS_USER:
        raise HTTPException(status_code=501, detail="Registracija kupaca još nije omogućena (potrebna migracija).")
    exists = db.query(UserModel).filter(UserModel.email == body.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="E-mail je već registrovan.")
    user = UserModel(
        email=body.email,
        full_name=body.full_name,
        password_hash=_hash_password(body.password),
        created_at=datetime.utcnow(),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.email, "role": "customer"})
    return {"access_token": token, "token_type": "bearer", "role": "customer"}

# -----------------------------------------------------------------------------
# Partner guard
# -----------------------------------------------------------------------------
def require_partner(identity=Depends(get_current_identity)):
    if identity.get("role") != "partner":
        raise HTTPException(status_code=403, detail="Dozvoljen pristup samo partnerima.")
    return identity

# -----------------------------------------------------------------------------
# Partners (za baner na frontendu)
# -----------------------------------------------------------------------------
@app.get("/partners")
def list_partners(db: Session = Depends(get_db)):
    if PartnerModel is None:
        return []
    rows = db.query(PartnerModel).order_by(asc(PartnerModel.id)).all()
    return [
        {
            "id": p.id,
            "naziv": p.naziv,
            "adresa": p.adresa,
            "lat": p.lat,
            "lng": p.lng,
            "thumbnail_url": p.thumbnail_url,
        }
        for p in rows
    ]

# -----------------------------------------------------------------------------
# PARTNER — Bags (uskladjeno sa src/api.js)
# -----------------------------------------------------------------------------
@app.get("/partner/bags/page")
def partner_bags_page(
    identity=Depends(require_partner),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    sort_by: str = Query("id"),
    sort_dir: str = Query("desc"),
    search: Optional[str] = None,
):
    if BagModel is None:
        return {"items": [], "total": 0, "page": page, "size": page_size, "pages": 0}
    q = db.query(BagModel).filter(BagModel.partner_id == identity["id"])
    if search:
        s = f"%{search}%"
        q = q.filter(or_(BagModel.naziv.ilike(s), BagModel.opis.ilike(s)))
    sort_col = getattr(BagModel, sort_by, getattr(BagModel, "id"))
    q = q.order_by(desc(sort_col) if sort_dir == "desc" else asc(sort_col))
    total = q.count()
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    items = [
        {
            "id": r.id,
            "naziv": r.naziv,
            "opis": r.opis,
            "cena": float(r.cena),
            "kolicina": r.kolicina,
            "vreme_preuzimanja": r.vreme_preuzimanja,
            "status": r.status,
            "partner_id": r.partner_id,
            "adresa": r.adresa,
            "lat": r.lat,
            "lng": r.lng,
            "thumbnail_url": r.thumbnail_url,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    pages = (total + page_size - 1) // page_size
    return {"items": items, "total": total, "page": page, "size": page_size, "pages": pages}

@app.get("/partner/bags/counts")
def partner_bag_counts(identity=Depends(require_partner), db: Session = Depends(get_db)):
    if BagModel is None:
        return {"total": 0, "active": 0, "sold_out": 0}
    q = db.query(BagModel).filter(BagModel.partner_id == identity["id"])
    total = q.count()
    active = q.filter(BagModel.status == "active").count()
    sold = q.filter(BagModel.status == "sold_out").count()
    return {"total": total, "active": active, "sold_out": sold}

@app.get("/partner/bags/export")
def partner_bags_export(
    identity=Depends(require_partner),
    db: Session = Depends(get_db),
    search: Optional[str] = None,
    sort_by: str = Query("id"),
    sort_dir: str = Query("desc"),
):
    if BagModel is None:
        raise HTTPException(status_code=500, detail="Bag model nije dostupan.")
    q = db.query(BagModel).filter(BagModel.partner_id == identity["id"])
    if search:
        s = f"%{search}%"
        q = q.filter(or_(BagModel.naziv.ilike(s), BagModel.opis.ilike(s)))
    sort_col = getattr(BagModel, sort_by, getattr(BagModel, "id"))
    q = q.order_by(desc(sort_col) if sort_dir == "desc" else asc(sort_col))
    rows = q.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id","naziv","opis","cena","kolicina","vreme_preuzimanja","status","adresa","lat","lng","thumbnail_url","created_at"])
    for r in rows:
        writer.writerow([
            r.id, r.naziv, r.opis, float(r.cena), r.kolicina,
            r.vreme_preuzimanja.isoformat() if r.vreme_preuzimanja else "",
            r.status, r.adresa, r.lat, r.lng, r.thumbnail_url,
            r.created_at.isoformat() if r.created_at else ""
        ])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8")

@app.post("/partner/bags")
def create_bag(
    body: schemas.BagCreate,
    identity=Depends(require_partner),
    db: Session = Depends(get_db),
):
    if BagModel is None:
        raise HTTPException(status_code=500, detail="Bag model nije dostupan.")
    bag = BagModel(
        naziv=body.naziv,
        opis=body.opis,
        cena=body.cena,
        kolicina=body.kolicina,
        vreme_preuzimanja=body.vreme_preuzimanja,
        status=body.status or "active",
        partner_id=identity["id"],
        adresa=body.adresa,
        lat=body.lat,
        lng=body.lng,
        thumbnail_url=body.thumbnail_url,
        created_at=datetime.utcnow(),
    )
    db.add(bag)
    db.commit()
    db.refresh(bag)
    return {"id": bag.id, "naziv": bag.naziv, "opis": bag.opis, "cena": float(bag.cena),
            "kolicina": bag.kolicina, "vreme_preuzimanja": bag.vreme_preuzimanja,
            "status": bag.status, "partner_id": bag.partner_id, "adresa": bag.adresa,
            "lat": bag.lat, "lng": bag.lng, "thumbnail_url": bag.thumbnail_url, "created_at": bag.created_at}

@app.put("/partner/bags/{bag_id}")
def update_bag(
    bag_id: int,
    body: schemas.BagUpdate,
    identity=Depends(require_partner),
    db: Session = Depends(get_db),
):
    if BagModel is None:
        raise HTTPException(status_code=500, detail="Bag model nije dostupan.")
    bag = db.query(BagModel).filter(BagModel.id == bag_id, BagModel.partner_id == identity["id"]).first()
    if not bag:
        raise HTTPException(status_code=404, detail="Kesa nije pronađena.")
    for field in ["naziv","opis","cena","kolicina","vreme_preuzimanja","status","adresa","lat","lng","thumbnail_url"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(bag, field, val)
    db.commit()
    db.refresh(bag)
    return {"id": bag.id, "naziv": bag.naziv, "opis": bag.opis, "cena": float(bag.cena),
            "kolicina": bag.kolicina, "vreme_preuzimanja": bag.vreme_preuzimanja,
            "status": bag.status, "partner_id": bag.partner_id, "adresa": bag.adresa,
            "lat": bag.lat, "lng": bag.lng, "thumbnail_url": bag.thumbnail_url, "created_at": bag.created_at}

@app.delete("/partner/bags/{bag_id}")
def delete_bag(bag_id: int, identity=Depends(require_partner), db: Session = Depends(get_db)):
    if BagModel is None:
        raise HTTPException(status_code=500, detail="Bag model nije dostupan.")
    bag = db.query(BagModel).filter(BagModel.id == bag_id, BagModel.partner_id == identity["id"]).first()
    if not bag:
        raise HTTPException(status_code=404, detail="Kesa nije pronađena.")
    db.delete(bag)
    db.commit()
    return {"ok": True}

@app.patch("/partner/bags/{bag_id}/status")
def set_bag_status(bag_id: int, status_value: str, identity=Depends(require_partner), db: Session = Depends(get_db)):
    if BagModel is None:
        raise HTTPException(status_code=500, detail="Bag model nije dostupan.")
    bag = db.query(BagModel).filter(BagModel.id == bag_id, BagModel.partner_id == identity["id"]).first()
    if not bag:
        raise HTTPException(status_code=404, detail="Kesa nije pronađena.")
    bag.status = status_value
    db.commit()
    return {"ok": True}

# -----------------------------------------------------------------------------
# PUBLIC — Bags
# -----------------------------------------------------------------------------
@app.get("/public/bags/page")
def public_bags_page(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    category: Optional[str] = None,
    sort_by: str = Query("id"),
    sort_dir: str = Query("desc"),
    within_km: Optional[float] = Query(None, alias="radius_km"),
    lat: Optional[float] = None,
    lng: Optional[float] = None,
):
    if BagModel is None:
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    q = db.query(BagModel).filter(BagModel.status == "active")
    if search:
        s = f"%{search}%"
        q = q.filter(or_(BagModel.naziv.ilike(s), BagModel.opis.ilike(s)))
    if min_price is not None:
        q = q.filter(BagModel.cena >= min_price)
    if max_price is not None:
        q = q.filter(BagModel.cena <= max_price)
    if within_km and lat is not None and lng is not None:
        import math
        km_per_deg_lat = 111.0
        km_per_deg_lng = 111.0 * max(0.1, abs(math.cos(math.radians(lat))))
        dlat = within_km / km_per_deg_lat
        dlng = within_km / km_per_deg_lng
        q = q.filter(
            BagModel.lat.between(lat - dlat, lat + dlat),
            BagModel.lng.between(lng - dlng, lng + dlng),
        )
    total = q.count()
    sort_col = getattr(BagModel, sort_by, getattr(BagModel, "id"))
    q = q.order_by(desc(sort_col) if sort_dir == "desc" else asc(sort_col))
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for r in rows:
        items.append({
            "id": r.id,
            "naziv": r.naziv,
            "opis": r.opis,
            "cena": float(r.cena),
            "kolicina": r.kolicina,
            "vreme_preuzimanja": r.vreme_preuzimanja,
            "status": r.status,
            "partner_id": r.partner_id,
            "adresa": r.adresa,
            "lat": r.lat,
            "lng": r.lng,
            "thumbnail_url": r.thumbnail_url,
        })
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@app.get("/public/bags/{bag_id}")
def public_bag_details(bag_id: int, db: Session = Depends(get_db)):
    if BagModel is None:
        raise HTTPException(status_code=404, detail="Kesa nije pronađena.")
    r = db.query(BagModel).filter(BagModel.id == bag_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Kesa nije pronađena.")
    return {
        "id": r.id,
        "naziv": r.naziv,
        "opis": r.opis,
        "cena": float(r.cena),
        "kolicina": r.kolicina,
        "vreme_preuzimanja": r.vreme_preuzimanja,
        "status": r.status,
        "partner_id": r.partner_id,
        "adresa": r.adresa,
        "lat": r.lat,
        "lng": r.lng,
        "thumbnail_url": r.thumbnail_url,
        "created_at": r.created_at,
    }

@app.post("/public/bags/{bag_id}/reserve")
def public_bag_reserve(bag_id: int, db: Session = Depends(get_db)):
    if BagModel is None:
        raise HTTPException(status_code=404, detail="Kesa nije pronađena.")
    bag = db.query(BagModel).filter(BagModel.id == bag_id).first()
    if not bag:
        raise HTTPException(status_code=404, detail="Kesa nije pronađena.")
    if bag.status != "active" or bag.kolicina <= 0:
        raise HTTPException(status_code=400, detail="Kesa nije dostupna.")
    bag.kolicina -= 1
    if bag.kolicina <= 0:
        bag.status = "sold_out"
    db.commit()
    return {"ok": True, "bag_id": bag.id, "remaining": bag.kolicina, "status": bag.status}

# -----------------------------------------------------------------------------
# Upload (apsolutni URL!)
# -----------------------------------------------------------------------------
@app.post("/upload/image")
def upload_image(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower() or ".bin"
    safe_name = f"{uuid.uuid4().hex}{ext}"
    dst = os.path.join(UPLOAD_DIR, safe_name)
    with open(dst, "wb") as f:
        f.write(file.file.read())
    rel = f"/static/uploads/{safe_name}"
    abs_url = f"{BACKEND_PUBLIC_URL}{rel}"
    return {"url": abs_url, "path": rel}

# -----------------------------------------------------------------------------
# Health
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True, "time": datetime.utcnow().isoformat()}
