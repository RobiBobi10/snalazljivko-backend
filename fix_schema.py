# fix_schema.py
from sqlalchemy import inspect, text
from database import engine

def ensure_partner_created_at():
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("partners", schema="public")}
    if "created_at" not in cols:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE public.partners ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW()"))
        print(">> Dodata kolona partners.created_at")
    else:
        print(">> Kolona partners.created_at već postoji")

def ensure_bag_created_at():
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("bags", schema="public")}
    if "created_at" not in cols:
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE public.bags ADD COLUMN created_at TIMESTAMPTZ DEFAULT NOW()"))
        print(">> Dodata kolona bags.created_at")
    else:
        print(">> Kolona bags.created_at već postoji")

if __name__ == "__main__":
    ensure_partner_created_at()
    ensure_bag_created_at()
    print(">> Schema fix gotov.")
