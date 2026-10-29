from abc import ABC, abstractmethod

import pandas as pd


class StagingRepository(ABC):
    @abstractmethod
    def ensure_schema(self, schema_name: str) -> None:
        """Create schema if it does not exist."""

    @abstractmethod
    def write_dataframe(self, df: pd.DataFrame, table_name: str, schema_name: str) -> None:
        """Persist a DataFrame into PostgreSQL staging schema."""

    @abstractmethod
    def get_max_value(
        self,
        table_name: str,
        schema_name: str,
        column_name: str,
    ):
        """Return the maximum value in a table column, or None if the table is empty."""

    @abstractmethod
    def upsert_dataframe(
        self,
        df: pd.DataFrame,
        table_name: str,
        schema_name: str,
        key_column: str,
    ) -> None:
        """Insert or update rows using a unique key column."""
