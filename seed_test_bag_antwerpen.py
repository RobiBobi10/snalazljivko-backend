# seed_test_bag_antwerpen.py
import requests

API_URL = "http://localhost:8000"  # ili tvoj backend URL na Renderu
USERNAME = "partner"
PASSWORD = "tajna"

# 1. Login i uzmi token
res = requests.post(f"{API_URL}/token", data={"username": USERNAME, "password": PASSWORD})
res.raise_for_status()
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Nađi partnera (uzima prvog iz liste)
partners = requests.get(f"{API_URL}/partners", headers=headers).json()
if not partners:
    raise SystemExit("Nema partnera u bazi. Prvo dodaj partnera.")

partner_id = partners[0]["id"]

# 3. Podaci za test bag u Antwerpenu
payload = {
    "naziv": "Test Bag Antwerpen",
    "opis": "Test kesica za geolokaciju u Antwerpenu",
    "cena": 5.0,
    "kolicina": 3,
    "status": "active",
    "partner_id": partner_id,
    "adresa": "Antwerpen, Belgija",
    "lat": 51.2194,   # Antwerpen centar
    "lng": 4.4025,
    "vreme_preuzimanja": None,
    "thumbnail_url": None
}

# 4. Kreiraj kesu
res = requests.post(f"{API_URL}/partner/bags", json=payload, headers=headers)
res.raise_for_status()
print("Test bag kreiran:", res.json())
