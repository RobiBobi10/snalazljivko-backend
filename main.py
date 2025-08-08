from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API radi!"}

git add main.py
git commit -m "Dodao osnovnu FastAPI aplikaciju"
git push

from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "API radi! Dobrodošao na Snalazljivko backend 🚀"}
