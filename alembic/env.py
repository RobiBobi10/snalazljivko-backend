from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# >>> dodato: čitaj URL iz našeg database.py
import database
import models

config = context.config
fileConfig(config.config_file_name)

# koristimo isti metadata kao app
target_metadata = models.Base.metadata

def run_migrations_offline():
    url = database.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = database.DATABASE_URL  # ključna linija
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
