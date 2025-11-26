import os
from abc import ABC, abstractmethod
from itertools import chain

from pysqlscribe.table import Table
from pysqlscribe.utils.ddl_loader import load_tables_from_ddls

file_path = os.path.dirname(__file__)
project_root = os.path.dirname(file_path)
ddl_path = os.path.join(project_root, "ddl")


class CardStore(ABC):
    _type: str = "default"

    @classmethod
    def get_card_store(cls, type: str) -> "CardStore":
        try:
            subclasses = cls.__subclasses__()
            subclasses_of_subclasses = list(
                chain(*(subcls.__subclasses__() for subcls in subclasses))
            )
            all_subclasses = subclasses + subclasses_of_subclasses
            return next(
                (subclass() for subclass in all_subclasses if subclass._type == type)
            )
        except StopIteration:
            raise ValueError(f"Unsupported card store type: {type}")


class CardStoreRDBMS(CardStore):
    _type: str = "rdbms"

    def __init__(self):
        self.tables = load_tables_from_ddls(ddl_path, self._type)

    @property
    def card_table(self) -> Table:
        return self.tables["cards"]

    @property
    @abstractmethod
    def connection_string(self) -> str: ...


class CardStoreInMemory(CardStore):
    _type: str = "in_memory"


class CardStoreSQLite(CardStoreRDBMS):
    _type: str = "sqlite"

    @property
    def connection_string(self) -> str:
        return "sqlite:///:memory:"


class CardStorePostgres(CardStoreRDBMS):
    _type: str = "postgres"

    @property
    def connection_string(self) -> str:
        from os import getenv

        pg_user, pg_password, pg_host, pg_port, pg_database = (
            getenv("POSTGRES_USER"),
            getenv("POSTGRES_PASSWORD"),
            getenv("POSTGRES_HOST"),
            getenv("POSTGRES_PORT"),
            getenv("POSTGRES_DB"),
        )
        return f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
