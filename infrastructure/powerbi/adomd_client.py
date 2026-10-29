import logging
from typing import Optional

import pandas as pd

from domain.ports.power_bi_reader import PowerBIReader
from infrastructure.powerbi.power_bi_port_finder import ensure_adomd_available

logger = logging.getLogger(__name__)


class AdomdPowerBIReader(PowerBIReader):
    def __init__(self, connection_string: str):
        # Приймаємо готовий connection_string, сформований у фабриці/port finder
        self.connection_string = connection_string

    def get_table(
        self,
        table_name: str,
        limit: Optional[int] = None,
        after_index: Optional[int] = None,
        index_column: Optional[str] = None,
    ) -> pd.DataFrame:
        if limit is not None and limit <= 0:
            raise ValueError('limit must be a positive integer.')
        if after_index is not None and limit is None:
            raise ValueError('limit is required when after_index is provided.')
        if after_index is not None and index_column is None:
            raise ValueError('index_column is required when after_index is provided.')

        if not ensure_adomd_available():
            raise RuntimeError(
                'Microsoft.AnalysisServices.AdomdClient could not be loaded. '
                'Install ADOMD.NET or DAX Studio and verify its installation path.'
            )

        try:
            from pyadomd import Pyadomd
        except ImportError as exc:
            raise RuntimeError(
                'pyadomd is not installed. Install it to connect to Power BI.'
            ) from exc

        # Лапки обов'язкові для назв із дефісами та цифрами ('2018-2026')
        query = self._build_query(
            table_name,
            limit=limit,
            after_index=after_index,
            index_column=index_column,
        )
        
        try:
            with Pyadomd(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query)
                    data = cursor.fetchall()
                    columns = [col[0] for col in cursor.description]
                    return pd.DataFrame(data, columns=columns)
        except Exception as exc:
            logger.error("Failed to query table '%s' from Power BI: %s", table_name, exc)
            raise

    @staticmethod
    def _build_query(
        table_name: str,
        limit: Optional[int] = None,
        after_index: Optional[int] = None,
        index_column: Optional[str] = None,
    ) -> str:
        dax_table_name = table_name.replace("'", "''")
        if limit is None:
            return "EVALUATE '%s'" % dax_table_name

        if index_column is None:
            if after_index is not None:
                raise ValueError('index_column is required when after_index is provided.')
            return "EVALUATE TOPN(%s, '%s')" % (limit, dax_table_name)

        if after_index is None:
            return (
                "EVALUATE TOPN(%s, '%s', '%s'[%s], ASC)"
                % (limit, dax_table_name, dax_table_name, index_column)
            )

        return (
            "EVALUATE TOPN(%s, "
            "FILTER('%s', '%s'[%s] > %s), "
            "'%s'[%s], ASC)"
            % (
                limit,
                dax_table_name,
                dax_table_name,
                index_column,
                after_index,
                dax_table_name,
                index_column,
            )
        )