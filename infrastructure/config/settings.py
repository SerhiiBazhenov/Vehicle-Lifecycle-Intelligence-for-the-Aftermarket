import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def _load_environment_file() -> None:
    candidates = [
        Path(__file__).resolve().parents[2] / '.env',
        Path.cwd() / '.env',
    ]
    for env_path in candidates:
        if not env_path.exists():
            continue
        with env_path.open('r', encoding='utf-8') as handle:
            for line in handle:
                raw = line.strip()
                if not raw or raw.startswith('#') or '=' not in raw:
                    continue
                key, value = raw.split('=', 1)
                key = key.strip()
                value = value.strip().strip("\"'")
                os.environ.setdefault(key, value)


@dataclass(frozen=True)
class PowerBISettings:
    database_name: str = 'Auto_registration_Ukraine'
    port: Optional[int] = None
    dax_studio_path: str = r'C:\Program Files\DAX Studio\bin'
    bravo_path: str = r'C:\Program Files\SQLBI\Bravo'

    def connection_string(self) -> str:
        if self.port is None:
            raise ValueError('Power BI port is not configured.')
        return (
            'Provider=MSOLAP;'
            f'Data Source=localhost:{self.port};'
            'Integrated Security=SSPI;'
        )


@dataclass(frozen=True)
class PostgresSettings:
    user: str = 'admin'
    password: str = 'password123'
    host: str = 'localhost'
    port: int = 5432
    database: str = 'auto_reg_db'
    schema: str = 'stg'

    @property
    def connection_string(self) -> str:
        return (
            f'postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}'
        )


def load_settings() -> Tuple[PowerBISettings, PostgresSettings]:
    _load_environment_file()

    power_bi = PowerBISettings(
        database_name=os.getenv('POWERBI_DATABASE_NAME', 'Auto_registration_Ukraine'),
        port=_safe_int(os.getenv('POWERBI_PORT')),
    )

    postgres = PostgresSettings(
        user=os.getenv('POSTGRES_USER', 'admin'),
        password=os.getenv('POSTGRES_PASSWORD', 'password123'),
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=_safe_int(os.getenv('POSTGRES_PORT', '5432'), default=5432) or 5432,
        database=os.getenv('POSTGRES_DB', 'auto_reg_db'),
        schema=os.getenv('POSTGRES_SCHEMA', 'stg'),
    )

    logger.debug('Loaded Power BI and Postgres settings.')
    return power_bi, postgres


def _safe_int(value: Optional[str], default: Optional[int] = None) -> Optional[int]:
    if value is None or value == '':
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Value '%s' is not a valid integer; using default %s.", value, default)
        return default
