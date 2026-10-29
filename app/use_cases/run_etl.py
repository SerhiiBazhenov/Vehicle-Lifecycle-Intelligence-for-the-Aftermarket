import logging
import re
from typing import Optional, Sequence

from domain.ports.power_bi_reader import PowerBIReader
from domain.ports.staging_repository import StagingRepository

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_TABLES = [
    '2018-2026',
    'Dim',
    'Date',
    'Brand_model_Year',
    'Brand',
    'vin_wmi_all_prefix_combinations',
    'Auto_registration_monthly',
]

# Залишаємо порожнім, щоб уникнути батчингу в SSAS і помилки Memory Allocation failure
INCREMENTAL_INDEX_TABLES = {}
DEFAULT_BATCH_SIZE = 10000


class RunEtlUseCase:
    def __init__(
        self,
        power_bi_reader: PowerBIReader,
        staging_repository: StagingRepository,
        source_tables: Optional[Sequence[str]] = None,
        schema_name: str = 'stg',
        max_rows_per_table: Optional[int] = None,
        target_table_name: Optional[str] = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        if max_rows_per_table is not None and max_rows_per_table <= 0:
            raise ValueError('max_rows_per_table must be a positive integer.')
        if batch_size <= 0:
            raise ValueError('batch_size must be a positive integer.')
        if target_table_name is not None and len(source_tables or ()) != 1:
            raise ValueError('target_table_name can only be used with exactly one source table.')

        self.power_bi_reader = power_bi_reader
        self.staging_repository = staging_repository
        self.source_tables = list(
            DEFAULT_SOURCE_TABLES if source_tables is None else source_tables
        )
        self.schema_name = schema_name
        self.max_rows_per_table = max_rows_per_table
        self.target_table_name = target_table_name
        self.batch_size = batch_size

    def execute(self) -> None:
        logger.info("Ensuring schema %s exists in PostgreSQL...", self.schema_name)
        self.staging_repository.ensure_schema(self.schema_name)

        for table_name in self.source_tables:
            destination_table = self.target_table_name or table_name
            
            logger.info("Starting Full ETL Load for table '%s'...", table_name)

            # 1. Читаємо всі дані за один DAX-запит (або з лімітом max_rows_per_table, якщо вказано)
            df = self.power_bi_reader.get_table(
                table_name,
                limit=self.max_rows_per_table,
            )

            if df.empty:
                logger.warning("Table '%s' returned 0 rows. Skipping.", table_name)
                continue

            # 2. Швидко записуємо всі рядки у PostgreSQL через бінарний COPY
            self.staging_repository.write_dataframe(
                df=df,
                table_name=destination_table,
                schema_name=self.schema_name,
            )

            logger.info(
                "Successfully migrated %s rows from Power BI table '%s' to %s.%s.",
                len(df),
                table_name,
                self.schema_name,
                destination_table,
            )

        logger.info("ETL pipeline execution completed successfully.")