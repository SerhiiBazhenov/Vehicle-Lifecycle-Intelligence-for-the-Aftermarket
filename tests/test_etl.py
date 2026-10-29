import os
import unittest
from unittest.mock import patch

import pandas as pd

from app.use_cases.run_etl import RunEtlUseCase
from infrastructure.config.settings import load_settings


class FakePowerBIReader:
    def __init__(self, dataframe):
        self.dataframe = dataframe

    def get_table(self, table_name, limit=None):
        dataframe = self.dataframe.copy()
        return dataframe.head(limit) if limit is not None else dataframe


class FakeStagingRepository:
    def __init__(self):
        self.schema = None
        self.writes = []

    def ensure_schema(self, schema_name):
        self.schema = schema_name

    def write_dataframe(self, df, table_name, schema_name):
        self.writes.append((table_name, schema_name, len(df)))

    def get_max_value(self, table_name, schema_name, column_name):
        return None

    def upsert_dataframe(self, df, table_name, schema_name, key_column):
        self.writes.append((table_name, schema_name, len(df)))


class IncrementalPowerBIReader:
    def __init__(self, dataframe):
        self.dataframe = dataframe
        self.last_indexes = []

    def get_table(self, table_name, limit=None, after_index=None, index_column='Index'):
        self.last_indexes.append(after_index)
        dataframe = self.dataframe
        if after_index is not None:
            dataframe = dataframe[dataframe[index_column] > after_index]
        return dataframe.sort_values(index_column).head(limit).copy()

class SettingsTests(unittest.TestCase):
    def test_load_settings_uses_env_values(self):
        with patch.dict(
            os.environ,
            {
                'POWERBI_DATABASE_NAME': 'DemoModel',
                'POWERBI_PORT': '1234',
                'POSTGRES_USER': 'demo_user',
                'POSTGRES_PASSWORD': 'demo_pass',
                'POSTGRES_HOST': 'db.example.com',
                'POSTGRES_PORT': '5433',
                'POSTGRES_DB': 'demo_db',
                'POSTGRES_SCHEMA': 'raw',
            },
            clear=True,
        ):
            power_bi, postgres = load_settings()

            self.assertEqual(power_bi.database_name, 'DemoModel')
            self.assertEqual(power_bi.port, 1234)
            self.assertEqual(postgres.user, 'demo_user')
            self.assertEqual(postgres.password, 'demo_pass')
            self.assertEqual(postgres.host, 'db.example.com')
            self.assertEqual(postgres.port, 5433)
            self.assertEqual(postgres.database, 'demo_db')
            self.assertEqual(postgres.schema, 'raw')


class RunEtlUseCaseTests(unittest.TestCase):
    def test_execute_writes_dataframe_to_staging(self):
        df = pd.DataFrame([{'id': 1, 'name': 'A'}])
        reader = FakePowerBIReader(df)
        repository = FakeStagingRepository()
        use_case = RunEtlUseCase(
            reader,
            repository,
            source_tables=['DemoTable'],
            schema_name='raw',
        )

        use_case.execute()

        self.assertEqual(repository.schema, 'raw')
        self.assertEqual(repository.writes, [('DemoTable', 'raw', 1)])

    def test_execute_limits_rows_written_to_staging(self):
        df = pd.DataFrame([{'id': row} for row in range(150)])
        reader = FakePowerBIReader(df)
        repository = FakeStagingRepository()
        use_case = RunEtlUseCase(
            reader,
            repository,
            source_tables=['DemoTable'],
            max_rows_per_table=100,
        )

        use_case.execute()

        self.assertEqual(repository.writes, [('DemoTable', 'stg', 100)])

    def test_limited_run_writes_to_separate_test_table(self):
        df = pd.DataFrame([{'id': row} for row in range(1000)])
        reader = FakePowerBIReader(df)
        repository = FakeStagingRepository()
        use_case = RunEtlUseCase(
            reader,
            repository,
            source_tables=['Auto_registration_monthly'],
            max_rows_per_table=1000,
            target_table_name='auto_registration_monthly_test',
        )

        use_case.execute()

        self.assertEqual(
            repository.writes,
            [('auto_registration_monthly_test', 'stg', 1000)],
        )

    def test_reader_query_limits_rows_in_power_bi(self):
        from infrastructure.powerbi.adomd_client import AdomdPowerBIReader

        self.assertEqual(
            AdomdPowerBIReader._build_query('Auto_registration_monthly', 100),
            "EVALUATE TOPN(100, 'Auto_registration_monthly')",
        )

    def test_incremental_reader_query_uses_index_paging(self):
        from infrastructure.powerbi.adomd_client import AdomdPowerBIReader

        self.assertEqual(
            AdomdPowerBIReader._build_query(
                '2018-2026',
                limit=10000,
                after_index=123,
                index_column='Index',
            ),
            "EVALUATE TOPN(10000, FILTER('2018-2026', '2018-2026'[Index] > 123), '2018-2026'[Index], ASC)",
        )

    def test_2018_table_is_loaded_in_batches_using_index(self):
        from app.use_cases.run_etl import RunEtlUseCase

        reader = IncrementalPowerBIReader(
            pd.DataFrame({'Index': range(1, 6), 'value': list('abcde')})
        )
        repository = FakeStagingRepository()
        use_case = RunEtlUseCase(
            reader,
            repository,
            source_tables=['2018-2026'],
            batch_size=2,
        )

        use_case.execute()

        self.assertEqual(reader.last_indexes, [None, 2, 4, 5])
        self.assertEqual(
            repository.writes,
            [('2018-2026', 'stg', 2), ('2018-2026', 'stg', 2), ('2018-2026', 'stg', 1)],
        )


if __name__ == '__main__':
    unittest.main()
