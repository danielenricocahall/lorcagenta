from db.card_store import CardStore
import pytest


@pytest.mark.parametrize("store_type", ["sqlite", "postgres"])
def test_sqlite_card_store(store_type: str):
    card_store = CardStore.get_card_store(store_type)
    assert "lorcana_cards" in card_store.tables
