# debug_db.py
from sqlalchemy import inspect
from database import engine
import models

print(">> Creating tables if missing ...")
models.Base.metadata.create_all(bind=engine)

insp = inspect(engine)
print(">> Tables in DB:", insp.get_table_names(schema="public"))
