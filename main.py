import logging
import argparse
from dataclasses import replace
from typing import Optional

from app.use_cases.run_etl import DEFAULT_SOURCE_TABLES, RunEtlUseCase
from infrastructure.config.settings import load_settings
from infrastructure.powerbi.adomd_client import AdomdPowerBIReader
from infrastructure.powerbi.power_bi_port_finder import PowerBIPortFinderImpl, ensure_adomd_available
from infrastructure.postgres.staging_repository import PostgresStagingRepository

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_etl(
    table_name: Optional[str] = None,
    row_limit: Optional[int] = None,
) -> None:
    if row_limit is not None and row_limit <= 0:
        raise ValueError('row_limit must be a positive integer.')
    if table_name is not None and table_name not in DEFAULT_SOURCE_TABLES:
        raise ValueError('Unknown Power BI table: %s' % table_name)

    ensure_adomd_available()

    power_bi_settings, postgres_settings = load_settings()

    port = power_bi_settings.port or PowerBIPortFinderImpl().find_port()
    if port is None:
        raise RuntimeError(
            'Power BI Desktop is not running or its Analysis Services port could not be found.'
        )

    power_bi_settings = replace(power_bi_settings, port=port)

    logger.info('Starting ETL: Power BI (Port %s) -> PostgreSQL (Schema: %s)', port, postgres_settings.schema)

    reader = AdomdPowerBIReader(power_bi_settings.connection_string())
    repository = PostgresStagingRepository(postgres_settings.connection_string)
    if table_name is None and row_limit is not None:
        table_name = 'Auto_registration_monthly'
    target_table_name = (
        table_name.lower() + '_test'
        if row_limit is not None and table_name is not None
        else None
    )

    use_case = RunEtlUseCase(
        reader,
        repository,
        source_tables=[table_name] if table_name is not None else None,
        schema_name=postgres_settings.schema,
        max_rows_per_table=row_limit,
        target_table_name=target_table_name,
    )
    use_case.execute()

    logger.info('ETL migration to schema %s completed.', postgres_settings.schema)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Load Power BI tables into PostgreSQL.')
    parser.add_argument(
        '--table',
        choices=DEFAULT_SOURCE_TABLES,
        help='Load only this Power BI table.',
    )
    parser.add_argument(
        '--limit',
        type=int,
        help=(
            'Maximum number of rows to load. When used without --table, '
            'limits the run to Auto_registration_monthly.'
        ),
    )
    arguments = parser.parse_args()
    if arguments.limit is not None and arguments.limit <= 0:
        parser.error('--limit must be a positive integer.')

    run_etl(table_name=arguments.table, row_limit=arguments.limit)
