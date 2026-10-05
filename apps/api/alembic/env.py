from logging.config import fileConfig

from alembic import context
from app.config import get_settings
from app.models import tables  # noqa: F401 — register all models
from app.models.base import Base
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Exclude PostGIS internal tables and tiger/topology schemas."""
    if type_ == "table":
        if object.schema in ("tiger", "tiger_data", "topology"):
            return False
        POSTGIS_TABLES = {
            "spatial_ref_sys", "layer", "topology",
            "geocode_settings", "geocode_settings_default",
            "loader_platform", "loader_variables", "loader_lookuptables",
            "pagc_gaz", "pagc_lex", "pagc_rules",
            "zip_lookup", "zip_lookup_all", "zip_lookup_base",
            "zip_state", "zip_state_loc",
            "county_lookup", "countysub_lookup", "place_lookup",
            "state_lookup", "street_type_lookup", "secondary_unit_lookup",
            "direction_lookup", "tabblock", "tabblock20",
            "addr", "addrfeat", "bg", "county", "cousub", "edges",
            "faces", "featnames", "place", "state", "tract", "zcta5",
        }
        if name in POSTGIS_TABLES:
            return False
    return True


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
