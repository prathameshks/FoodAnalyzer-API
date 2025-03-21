import json
import os

def save_json_file(item, data):
    os.makedirs("v2", exist_ok=True)
    with open(f"v2/{item}.json", "w") as file:
        json.dump(data, file)
    print(f"Saved {item}.json")
