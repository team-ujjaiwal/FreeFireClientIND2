from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import random
import new_pb2
import logging
from secret import key, iv

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

def create_protobuf(player_id, region):
    player = new_pb2.FreeFirePlayer()
    
    # Set minimal required fields
    player.account.account_id = str(player_id)
    player.account.player_id = str(player_id)
    player.account.region = region.upper()
    
    return player.SerializeToString()

def get_jwt_token(region):
    try:
        uid, password = get_credentials(region)
        jwt_url = f"https://aditya-jwt-v9op.onrender.com/token?uid={uid}&password={password}"
        response = requests.get(jwt_url, timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"JWT token error: {str(e)}")
        return None

@app.route('/player-info', methods=['GET'])
def main():
    uid = request.args.get('uid')
    region = request.args.get('region')

    if not uid or not region:
        return jsonify({"error": "Missing parameters"}), 400

    # Get JWT token
    jwt_info = get_jwt_token(region)
    if not jwt_info:
        return jsonify({"error": "JWT token failure"}), 500

    logging.debug(f"JWT Info: {jwt_info}")

    # Prepare request
    try:
        protobuf_data = create_protobuf(uid, region)
        hex_data = binascii.hexlify(protobuf_data).decode()
        encrypted_data = encrypt_aes(hex_data, key, iv)
    except Exception as e:
        logging.error(f"Protobuf/encryption error: {str(e)}")
        return jsonify({"error": "Data preparation failed"}), 500

    # Make request to game server
    try:
        headers = {
            'Authorization': f'Bearer {jwt_info["token"]}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'GameClient/1.0'
        }
        
        logging.debug(f"Request URL: {jwt_info['serverUrl']}/GetPlayerPersonalShow")
        logging.debug(f"Headers: {headers}")
        
        response = requests.post(
            f"{jwt_info['serverUrl']}/GetPlayerPersonalShow",
            data=bytes.fromhex(encrypted_data),
            headers=headers,
            timeout=10
        )
        
        logging.debug(f"Response status: {response.status_code}")
        logging.debug(f"Response content: {response.content[:100]}...")
        
        response.raise_for_status()
        
        # Process response
        player_data = new_pb2.FreeFirePlayer()
        player_data.ParseFromString(response.content)
        return jsonify({"status": "success", "player_id": player_data.account.player_id})
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Server request failed: {str(e)}")
        return jsonify({
            "error": "Server communication failed",
            "details": str(e),
            "request_url": f"{jwt_info.get('serverUrl', '')}/GetPlayerPersonalShow"
        }), 502
    except Exception as e:
        logging.error(f"Response processing failed: {str(e)}")
        return jsonify({"error": "Response processing failed"}), 500

def encrypt_aes(hex_data, key, iv):
    try:
        key = key.encode()[:16]
        iv = iv.encode()[:16]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_data = pad(bytes.fromhex(hex_data), AES.block_size)
        return binascii.hexlify(cipher.encrypt(padded_data)).decode()
    except Exception as e:
        logging.error(f"Encryption failed: {str(e)}")
        raise

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)