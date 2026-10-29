import csv
import hashlib
from io import StringIO
import logging
import re
from typing import Any, Optional
from uuid import uuid4

import pandas as pd
from sqlalchemy import create_engine, inspect, text

from domain.ports.staging_repository import StagingRepository

logger = logging.getLogger(__name__)


def _psql_insert_copy(table, conn, keys, data_iter):
    """Швидкий метод вставки для pandas to_sql з використанням протоколу COPY в PostgreSQL."""
    dbapi_conn = conn.connection
    with dbapi_conn.cursor() as cur:
        s_buf = StringIO()
        writer = csv.writer(s_buf)
        writer.writerows(data_iter)
        s_buf.seek(0)

        columns = ', '.join([f'"{k}"' for k in keys])
        table_name = f'"{table.schema}"."{table.name}"' if table.schema else f'"{table.name}"'

        sql = f'COPY {table_name} ({columns}) FROM STDIN WITH CSV'
        cur.copy_expert(sql=sql, file=s_buf)


class PostgresStagingRepository(StagingRepository):
    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)

    def ensure_schema(self, schema_name: str) -> None:
        logger.info('Ensuring schema %s exists in PostgreSQL.', schema_name)
        with self.engine.connect() as conn:
            conn.execute(
                text(
                    'CREATE SCHEMA IF NOT EXISTS %s'
                    % self._quote_identifier(self._clean_sql_identifier(schema_name))
                )
            )
            conn.commit()

    def write_dataframe(self, df: pd.DataFrame, table_name: str, schema_name: str) -> None:
        clean_name = self._clean_sql_identifier(table_name)
        logger.info('Writing %s rows to PostgreSQL table %s.%s.', len(df), schema_name, clean_name)

        df = self._normalize_columns(df)

        df.to_sql(
            clean_name,
            con=self.engine,
            schema=schema_name,
            if_exists='replace',
            index=False,
            chunksize=100000,
            method=_psql_insert_copy,
        )
        logger.info('Successfully wrote %s rows to %s.%s.', len(df), schema_name, clean_name)

    def get_max_value(
        self,
        table_name: str,
        schema_name: str,
        column_name: str,
    ) -> Optional[Any]:
        clean_table = self._clean_sql_identifier(table_name)
        clean_column = self._clean_sql_identifier(column_name)
        if not inspect(self.engine).has_table(clean_table, schema=schema_name):
            return None

        qualified_table = self._qualified_name(schema_name, clean_table)
        quoted_column = self._quote_identifier(clean_column)
        with self.engine.connect() as conn:
            return conn.execute(
                text(
                    'SELECT MAX(%s) FROM %s'
                    % (quoted_column, qualified_table)
                )
            ).scalar()

    def upsert_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema_name: str,
        key_column: str,
    ) -> None:
        if df.empty:
            return

        clean_table = self._clean_sql_identifier(table_name)
        clean_key = self._clean_sql_identifier(key_column)
        normalized_df = self._normalize_columns(df)
        if clean_key not in normalized_df.columns:
            raise ValueError(
                'Upsert key column %r was not found in table %r.'
                % (key_column, table_name)
            )
        if normalized_df[clean_key].isnull().any():
            raise ValueError('Upsert key column %r contains null values.' % key_column)
        if normalized_df[clean_key].duplicated().any():
            raise ValueError('Upsert key column %r contains duplicates in the batch.' % key_column)

        qualified_table = self._qualified_name(schema_name, clean_table)
        quoted_key = self._quote_identifier(clean_key)
        index_digest = hashlib.sha1(
            ('%s.%s.%s' % (schema_name, clean_table, clean_key)).encode('utf-8')
        ).hexdigest()[:12]
        index_name = self._quote_identifier('uq_' + index_digest)
        columns = list(normalized_df.columns)
        quoted_columns = ', '.join(self._quote_identifier(column) for column in columns)
        updates = [
            '%s = EXCLUDED.%s'
            % (self._quote_identifier(column), self._quote_identifier(column))
            for column in columns
            if column != clean_key
        ]
        on_conflict = (
            'DO UPDATE SET ' + ', '.join(updates)
            if updates
            else 'DO NOTHING'
        )
        temp_table = 'etl_upsert_' + uuid4().hex
        quoted_temp_table = self._quote_identifier(temp_table)

        with self.engine.begin() as conn:
            if not inspect(conn).has_table(clean_table, schema=schema_name):
                normalized_df.head(0).to_sql(
                    clean_table,
                    con=conn,
                    schema=schema_name,
                    if_exists='fail',
                    index=False,
                )

            conn.execute(
                text(
                    'CREATE UNIQUE INDEX IF NOT EXISTS %s ON %s (%s)'
                    % (index_name, qualified_table, quoted_key)
                )
            )
            conn.execute(
                text(
                    'CREATE TEMP TABLE %s (LIKE %s INCLUDING DEFAULTS) ON COMMIT DROP'
                    % (quoted_temp_table, qualified_table)
                )
            )
            normalized_df.to_sql(
                temp_table,
                con=conn,
                if_exists='append',
                index=False,
                chunksize=100000,
                method=_psql_insert_copy,
            )
            conn.execute(
                text(
                    'INSERT INTO %s (%s) SELECT %s FROM %s '
                    % (
                        qualified_table,
                        quoted_columns,
                        quoted_columns,
                        quoted_temp_table,
                    )
                    + 'ON CONFLICT (%s) %s'
                    % (
                        quoted_key,
                        on_conflict,
                    )
                )
            )

        logger.info(
            'Upserted %s rows into %s.%s using key %s.',
            len(normalized_df),
            schema_name,
            clean_table,
            clean_key,
        )

    @classmethod
    def _normalize_columns(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Очищає назви колонок для SQL і автоматично розв'язує конфлікти дублікатів."""
        df = df.copy()
        new_columns = []
        seen_counts = {}

        for col in df.columns:
            clean_col = cls._clean_sql_identifier(str(col))
            if clean_col in seen_counts:
                seen_counts[clean_col] += 1
                unique_col = f"{clean_col}_{seen_counts[clean_col]}"
            else:
                seen_counts[clean_col] = 0
                unique_col = clean_col
            new_columns.append(unique_col)

        df.columns = new_columns
        return df

    @classmethod
    def _qualified_name(cls, schema_name: str, table_name: str) -> str:
        return '%s.%s' % (
            cls._quote_identifier(cls._clean_sql_identifier(schema_name)),
            cls._quote_identifier(table_name),
        )

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"%s"' % identifier.replace('"', '""')

    @staticmethod
    def _clean_sql_identifier(name: str) -> str:
        clean = re.sub(r'^.*?\[([^\]]+)\]$', r'\1', str(name))
        clean = re.sub(r'[^a-zA-Z0-9]', '_', clean)
        clean = re.sub(r'_+', '_', clean).lower().strip('_')
        if not clean or clean[0].isdigit():
            clean = f'col_{clean}'
        return clean