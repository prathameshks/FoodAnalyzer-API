import json
import hmac
import hashlib
import base64
import time
from datetime import datetime
from logger_manager import log_info, log_error
import os
import aiohttp

from env import VUFORIA_SERVER_ACCESS_KEY, VUFORIA_SERVER_SECRET_KEY,UPLOADED_IMAGES_DIR

async def add_target_to_vuforia(image_name: str, image_path: str) -> str:
    """
    Adds a target to the Vuforia database and returns the Vuforia target ID.
    Implements proper Vuforia authentication and request format.
    """
    log_info(f"Adding target {image_name} to Vuforia")

    try:
        # Read image data
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
        
        # Base64 encode the image
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Create request data
        request_path = '/targets'
        host = 'vws.vuforia.com'
        url = f"https://{host}{request_path}"
        
        # Create payload
        payload = {
            "name": image_name,
            "width": 150.0,  # Default width in scene units
            "image": image_base64,
            "active_flag": True,
        }
        
        # Convert payload to JSON
        body = json.dumps(payload)
        
        # Get current date in proper format for Vuforia
        date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # Set content type
        content_type = 'application/json'
        
        # Calculate MD5 of request body
        content_md5 = hashlib.md5(body.encode('utf-8')).hexdigest()
        
        # Create string to sign according to Vuforia docs
        string_to_sign = f"POST\n{content_md5}\n{content_type}\n{date}\n{request_path}"
        
        # Generate signature
        signature = hmac.new(
            VUFORIA_SERVER_SECRET_KEY.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
        signature_hex = base64.b64encode(signature).decode('utf-8')
        
        # Create headers
        headers = {
            'Authorization': f'VWS {VUFORIA_SERVER_ACCESS_KEY}:{signature_hex}',
            'Content-Type': content_type,
            'Date': date,
            'Content-MD5': content_md5
        }
        
        # Make the API request
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=body) as response:
                # Get response text and try to parse as JSON
                response_text = await response.text()
                try:
                    response_json = json.loads(response_text)
                except:
                    response_json = {"error": "Failed to parse response"}
                
                log_info(f"Vuforia response status: {response.status}")
                
                if response.status == 201:  # Created
                    log_info(f"Target added successfully: {response_json}")
                    return response_json.get("target_id", "unknown_target_id")
                else:
                    log_error(f"Failed to add target: Status {response.status}, Response: {response_text}")
                    raise Exception(f"Failed to add target {image_name}: Status {response.status}, Error: {response_json.get('result_code', 'Unknown')}")
                    
    except Exception as e:
        log_error(f"Error adding target {image_name}: {e}", e)
        raise