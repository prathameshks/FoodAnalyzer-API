import requests
import json
import os
from logger_manager import log_info, log_error

from env import VUFORIA_SERVER_ACCESS_KEY, VUFORIA_SERVER_SECRET_KEY

def get_vuforia_auth_headers():
    """
    Returns the authentication headers for Vuforia API requests.
    """
    return {
        "Authorization": f"VWS {VUFORIA_SERVER_ACCESS_KEY}:{VUFORIA_SERVER_SECRET_KEY}",
        "Content-Type": "application/json",
    }


async def add_target_to_vuforia(image_name: str, image_path: str) -> str:
    """
    Adds a target to the Vuforia database and returns the Vuforia target ID.
    """
    log_info(f"Adding target {image_name} to Vuforia")

    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()

        url = f"https://vws.vuforia.com/targets"

        headers = get_vuforia_auth_headers()
        payload = {
            "name": image_name,
            "width": 1.0,  # Default width
            "image": image_data.hex(),  # Convert image data to hex
            "active_flag": True,
        }

        response = requests.post(url, headers=headers, json=payload)
        response_data = json.loads(response.text)
        if response.status_code == 201:
            log_info(
                f"Target {image_name} added successfully with Vuforia ID: {response_data['target_id']}"
            )
            return response_data["target_id"]
        else:
            log_error(f"Failed to add target {image_name}: {response.text}")
            raise Exception(f"Failed to add target {image_name}: {response.text}")
    except Exception as e:
        log_error(f"Error adding target {image_name}: {e}", e)
        raise