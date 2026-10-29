from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd


class PowerBIReader(ABC):
    @abstractmethod
    def get_table(
        self,
        table_name: str,
        limit: Optional[int] = None,
        after_index: Optional[int] = None,
        index_column: Optional[str] = None,
    ) -> pd.DataFrame:
        """Return one table as DataFrame from Power BI."""


class PowerBIConnector(ABC):
    @abstractmethod
    def connect(self):
        """Open a connection to Power BI."""


class PowerBIPortFinder(ABC):
    @abstractmethod
    def find_port(self) -> Optional[int]:
        """Return the Power BI listening port or None if unavailable."""
