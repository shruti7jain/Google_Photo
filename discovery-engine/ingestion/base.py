import abc
from typing import Iterator

from models.schema import RawDocument


class SourceConnector(abc.ABC):
    """
    Abstract base class for all data ingestion connectors.
    """
    
    @abc.abstractmethod
    def fetch(self) -> Iterator[RawDocument]:
        """
        Fetches documents from the source and yields them as RawDocument objects.
        """
        pass
