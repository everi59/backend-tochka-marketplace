import asyncio
from logging.config import fileConfig
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
import sys
from os.path import abspath, dirname

# Добавляем корень проекта в PYTHONPATH
sys.path.insert(0, dirname(dirname(abspath(__file__))))

# ⭐ ВАЖНО: Укажи правильный путь к своему Base!
from app.infrastructure.database.models.base import Base  # <-- ПРОВЕРЬ ЭТОТ ПУТЬ

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations(conn):
    await conn.run_sync(do_run_migrations)


async def run_migrations_online() -> None:
    # Берём URL из alembic.ini или переопределяем из env/settings
    url = config.get_main_option("sqlalchemy.url")

    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await run_async_migrations(connection)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())