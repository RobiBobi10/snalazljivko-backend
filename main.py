from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from jose import JWTError, jwt
from datetime import datetime, timedelta

app = FastAPI()

# ✅ Dodaj CORS nakon što definišeš app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # ovde možeš dodati i frontend deploy kasnije
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dummy baza korisnika
fake_users_db = {
    "partner": {
        "username": "partner",
        "password": "tajna",  # Ovo je samo primer, bez hesiranja
        "role": "partner"
    }
}

# JWT konfiguracija
SECRET_KEY = "tajna_kljuc"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

class Token(BaseModel):
    access_token: str
    token_type: str

class Bag(BaseModel):
    id: int | None = None
    naziv: str
    opis: str
    tip: str
    cena: float
    vreme_preuzimanja: str
    kolicina: int


class Stats(BaseModel):
    broj_bagova: int
    broj_porudzbina: int
    ukupna_zarada: float

# In-memory podaci
bagovi = []
brojac_bagova = 1

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

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users_db.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=400, detail="Pogrešan username ili password")
    
    access_token = create_access_token(
        data={"sub": user["username"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/")
def read_root():
    return {"message": "API radi! Dobrodošao na Snalazljivko backend 🎒"}

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

@app.get("/partner/stats", response_model=Stats)
def get_stats(user: dict = Depends(verify_token)):
    broj_bagova = len(bagovi)
    broj_porudzbina = broj_bagova * 2  # primer logike
    ukupna_zarada = sum(b.cena * b.kolicina for b in bagovi)
    return Stats(
        broj_bagova=broj_bagova,
        broj_porudzbina=broj_porudzbina,
        ukupna_zarada=ukupna_zarada
    )
