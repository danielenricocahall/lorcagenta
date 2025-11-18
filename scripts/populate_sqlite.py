import json
import os

from scripts.retrieval import fetch_cards_data

import sqlite3

file_path = os.path.dirname(__file__)
project_root = os.path.dirname(file_path)
ddl_path = os.path.join(project_root, "ddl")


def normalize_value(v):
    """Convert unsupported types (lists, dicts) to JSON strings."""
    if isinstance(v, (list, dict)):
        return json.dumps(v)
    return v


def populate_sqlite_db(db_path: str):
    cards_data = fetch_cards_data()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    with open(ddl_path + "/create_card_table.sql", "r") as ddl_file:
        ddl_script = ddl_file.read()
        cursor.executescript(ddl_script)
    columns = list(cards_data["cards"][0].keys())
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT INTO lorcana_cards ({', '.join(columns)}) VALUES ({placeholders})"

    values = [
        tuple(normalize_value(card[col]) for col in columns)
        for card in cards_data["cards"]
    ]

    cursor.executemany(sql, values)
    cursor.connection.commit()


if __name__ == "__main__":
    db_path = f"{project_root}/cards.db"
    populate_sqlite_db(db_path)
    print(f"Database populated at {db_path}")
