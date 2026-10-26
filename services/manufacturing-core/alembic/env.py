from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("explicit migration DSN required")
    context.configure(
        url=url,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table_schema="core",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("explicit migration DSN required")
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        connection.exec_driver_sql(
            "CREATE SCHEMA IF NOT EXISTS core AUTHORIZATION CURRENT_USER"
        )
        context.configure(
            connection=connection,
            target_metadata=None,
            version_table_schema="core",
            version_table="alembic_version",
            runtime_role=config.attributes.get("runtime_role"),
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
