from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta

app = FastAPI()

# CORS – dodaj i prod URL ako bude trebalo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://snalazljivko-frontend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dummy korisnici (za demo) ---
fake_users_db = {
    "partner": {
        "username": "partner",
        "password": "tajna",  # samo primer (bez hash-a)
        "role": "partner",
    }
}

# --- JWT podešavanja ---
SECRET_KEY = "tajna_kljuc"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# --- Šeme ---
class Token(BaseModel):
    access_token: str
    token_type: str

class Bag(BaseModel):
    id: Optional[int] = None
    naziv: str
    opis: str
    tip: str
    cena: float
    vreme_preuzimanja: str
    kolicina: int
    status: str = "active"  # active | sold_out | archived

class BagUpdate(BaseModel):
    naziv: Optional[str] = None
    opis: Optional[str] = None
    tip: Optional[str] = None
    cena: Optional[float] = None
    vreme_preuzimanja: Optional[str] = None
    kolicina: Optional[int] = None
    status: Optional[str] = None

class Stats(BaseModel):
    broj_bagova: int
    broj_porudzbina: int
    ukupna_zarada: float

# --- In-memory skladište (demo) ---
bagovi: list[Bag] = []
brojac_bagova = 1

# --- JWT helpers ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Neispravan token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None or username not in fake_users_db:
            raise credentials_exception
        return fake_users_db[username]
    except JWTError:
        raise credentials_exception

# --- Auth ---
@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users_db.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=400, detail="Pogrešan username ili password")
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Health ---
@app.get("/")
def read_root():
    return {"message": "API radi! Dobrodošao na Snalazljivko backend 🎒"}

# --- Partner: Bags ---
@app.get("/partner/bags", response_model=List[Bag])
def get_bags(user: dict = Depends(verify_token)):
    return bagovi

@app.post("/partner/bags", response_model=Bag)
def create_bag(bag: Bag, user: dict = Depends(verify_token)):
    global brojac_bagova
    bag.id = brojac_bagova
    brojac_bagova += 1
    bagovi.append(bag)
    return bag

@app.put("/partner/bags/{bag_id}", response_model=Bag)
def update_bag(bag_id: int, patch: BagUpdate, user: dict = Depends(verify_token)):
    for i, b in enumerate(bagovi):
        if b.id == bag_id:
            data = b.dict()
            patch_data = {k: v for k, v in patch.dict().items() if v is not None}
            data.update(patch_data)
            bagovi[i] = Bag(**data)
            return bagovi[i]
    raise HTTPException(status_code=404, detail="Bag nije pronađen")

@app.delete("/partner/bags/{bag_id}", status_code=204)
def delete_bag(bag_id: int, user: dict = Depends(verify_token)):
    global bagovi
    before = len(bagovi)
    bagovi = [b for b in bagovi if b.id != bag_id]
    if len(bagovi) == before:
        raise HTTPException(status_code=404, detail="Bag nije pronađen")
    return

@app.patch("/partner/bags/{bag_id}/status", response_model=Bag)
def set_bag_status(bag_id: int, status_value: str, user: dict = Depends(verify_token)):
    if status_value not in {"active", "sold_out", "archived"}:
        raise HTTPException(status_code=400, detail="Pogrešan status")
    for i, b in enumerate(bagovi):
        if b.id == bag_id:
            bagovi[i].status = status_value
            return bagovi[i]
    raise HTTPException(status_code=404, detail="Bag nije pronađen")

# --- Statistika ---
@app.get("/partner/stats", response_model=Stats)
@app.get("/partner/stats", response_model=Stats)
def get_stats(user: dict = Depends(verify_token)):
    broj_bagova = len(bagovi)
    # Pretpostavka: "porudžbina" ~ ukupno komada (sum(kolicina)) dok ne uvedemo prave narudžbine
    broj_porudzbina = sum(b.kolicina for b in bagovi)
    ukupna_zarada = sum(b.cena * b.kolicina for b in bagovi)
    return Stats(
        broj_bagova=broj_bagova,
        broj_porudzbina=broj_porudzbina,
        ukupna_zarada=ukupna_zarada
    )

