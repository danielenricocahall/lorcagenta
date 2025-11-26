import os
import sqlite3
from abc import ABC, abstractmethod
from itertools import chain

from pysqlscribe.table import Table
from pysqlscribe.utils.ddl_loader import load_tables_from_ddls
from pysqlscribe.scalar_functions import lower

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

    @abstractmethod
    def get_cards(
        self, color: str | None = None, name: str | None = None, cost: int | None = None
    ) -> list[dict]: ...

    @property
    def color_to_id_mapping(self):
        return {
            "ruby": 1,
            "sapphire": 2,
            "emerald": 3,
            "amber": 4,
            "amethyst": 5,
            "steel": 6,
        }

    @property
    def id_to_color_mapping(self):
        return {v: k for k, v in self.card_number_to_color_mapping.items()}


class CardStoreRDBMS(CardStore):
    _type: str = "rdbms"

    def __init__(self):
        self.tables = load_tables_from_ddls(ddl_path, self._type)

    @property
    def card_table(self) -> Table:
        return self.tables["lorcana_cards"]

    @property
    @abstractmethod
    def connection_string(self) -> str: ...

    def get_cards(
        self, color: str | None = None, name: str | None = None, cost: int | None = None
    ) -> list[dict]:
        query = self.card_table.select("*")
        clauses = []
        if color:
            clauses.append(self.card_table.color == self.color_to_id_mapping[color])
        if cost is not None:
            clauses.append(self.card_table.cost == cost)
        if name:
            clauses.append(lower(self.card_table.name) == name.lower())
        if clauses:
            query = query.where(*clauses)
        return self._get_cards_from_db(query.build())

    @abstractmethod
    def _get_cards_from_db(self, query: str) -> list[dict]:
        raise NotImplementedError("Subclasses must implement this method")


class CardStoreInMemory(CardStore):
    _type: str = "in_memory"


class CardStoreSQLite(CardStoreRDBMS):
    _type: str = "sqlite"

    @property
    def connection_string(self) -> str:
        return os.path.join(project_root, "cards.db")

    def _get_cards_from_db(self, query: str) -> list[dict]:
        with sqlite3.connect(self.connection_string) as conn:
            cursor = conn.cursor()
            cursor.execute(str(query))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in rows]


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


if __name__ == "__main__":
    card_store = CardStore.get_card_store("sqlite")
    cards = card_store.get_cards(color="sapphire", name="nick wilde")
    print(f"Retrieved {len(cards)} cards")
