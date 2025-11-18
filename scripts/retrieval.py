import os

import requests
import json

file_path = os.path.dirname(__file__)
project_root = os.path.dirname(file_path)

LORCANA_API = "https://lorcania.com/api/cardsSearch"
CARDS_PATH = f"{project_root}/lorcana_cards.json"


def fetch_cards_data():
    if os.path.exists(CARDS_PATH):
        with open(CARDS_PATH, "r") as file:
            results = json.load(file)
            return results
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
    }

    data = {
        "colors": [],
        "sets": [],
        "traits": [],
        "keywords": [],
        "costs": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        "inkwell": [],
        "rarity": [],
        "language": "English",
        "options": [],
        "sorting": "default",
    }

    response = requests.post(LORCANA_API, headers=headers, data=json.dumps(data))
    results = response.json()
    with open(CARDS_PATH, "w") as file:
        file.write(json.dumps(results, indent=4))

    return results
