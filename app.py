from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import random
import uid_generator_pb2
import freefire_pb2
from secret import key, iv

app = Flask(__name__)

def hex_to_bytes(hex_string):
    return bytes.fromhex(hex_string)

def create_protobuf(akiru_, aditya):
    message = uid_generator_pb2.uid_generator()
    message.akiru_ = akiru_
    message.aditya = aditya
    return message.SerializeToString()

def protobuf_to_hex(protobuf_data):
    return binascii.hexlify(protobuf_data).decode()

def decode_hex(hex_string):
    byte_data = binascii.unhexlify(hex_string.replace(' ', ''))
    users = CSGetPlayerPersonalShowRes()
    users.ParseFromString(byte_data)
    return users

def encrypt_aes(hex_data, key, iv):
    key = key.encode()[:16]
    iv = iv.encode()[:16]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(bytes.fromhex(hex_data), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    return binascii.hexlify(encrypted_data).decode()

def get_credentials(region):
    region = region.upper()
    if region == "IND":
        return "3942037420", "A0BF31A2E867E1619013C57462DFCF8D08102552EFB060FAE9A1213C3F331F25"
    elif region in ["NA", "BR", "SAC", "US"]:
        return "uid", "password"
    else:
        return "uid", "password"

def get_jwt_token(region):
    uid, password = get_credentials(region)
    jwt_url = f"https://jwt-aditya.vercel.app/token?uid={uid}&password={password}"
    response = requests.get(jwt_url)
    if response.status_code != 200:
        return None
    return response.json()

@app.route('/player-info', methods=['GET'])
def main():
    uid = request.args.get('uid')
    region = request.args.get('region')

    if not uid or not region:
        return jsonify({"error": "Missing 'uid' or 'region' query parameter"}), 400

    try:
        saturn_ = int(uid)
    except ValueError:
        return jsonify({"error": "Invalid UID"}), 400

    jwt_info = get_jwt_token(region)
    if not jwt_info or 'token' not in jwt_info:
        return jsonify({"error": "Failed to fetch JWT token"}), 500

    api = jwt_info['serverUrl']
    token = jwt_info['token']

    protobuf_data = create_protobuf(saturn_, 1)
    hex_data = protobuf_to_hex(protobuf_data)
    encrypted_hex = encrypt_aes(hex_data, key, iv)

    headers = {
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)',
        'Connection': 'Keep-Alive',
        'Expect': '100-continue',
        'Authorization': f'Bearer {token}',
        'X-Unity-Version': '2018.4.11f1',
        'X-GA': 'v1 1',
        'ReleaseVersion': 'OB49',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    try:
        response = requests.post(f"{api}/GetPlayerPersonalShow", headers=headers, data=bytes.fromhex(encrypted_hex))
        response.raise_for_status()
    except requests.RequestException:
        return jsonify({"error": "Failed to contact game server"}), 502

    hex_response = response.content.hex()

    try:
        response_data = freefire_pb2.GetPlayerPersonalShowResponse()
        response_data.ParseFromString(bytes.fromhex(hex_response))
    except Exception as e:
        return jsonify({"error": f"Failed to parse Protobuf: {str(e)}"}), 500

    result = {}

    # Player Info (field1)
    if response_data.field1:
        player = response_data.field1
        player_data = {
            'user_id': player.user_id,
            'account_type': player.account_type,
            'username': player.username,
            'country': player.country,
            'level': player.level,
            'experience': player.experience,
            'coin_id': player.coin_id,
            'diamond_id': player.diamond_id,
            'wins': player.wins,
            'kill_count': player.kill_count,
            'rank': player.rank,
            'character_id': player.character_id,
            'battle_count': player.battle_count,
            'headshot_count': player.headshot_count,
            'last_login': player.last_login,
            'ranked_points': player.ranked_points,
            'survival_mastery': player.survival_mastery,
            'encrypted_data': player.encrypted_data.hex() if player.encrypted_data else None,
            'pet_id': player.pet_id,
            'game_version': player.game_version if hasattr(player, 'game_version') else None,
            'is_online': player.is_online if hasattr(player, 'is_online') else None,
            'in_match': player.in_match if hasattr(player, 'in_match') else None
        }
        
        # Premium Info
        if player.HasField("premium"):
            player_data['premium'] = {
                'field4': player.premium.field4.hex() if player.premium.field4 else None,
                'field5': player.premium.field5.hex() if player.premium.field5 else None,
                'vip_level': player.premium.vip_level
            }
        
        # Settings
        if player.HasField("settings"):
            player_data['settings'] = {
                'control_type': player.settings.control_type,
                'sensitivity': player.settings.sensitivity
            }
        
        # Items
        if player.items:
            player_data['items'] = []
            for item in player.items:
                item_data = {
                    'item_id': item.item_id,
                    'quantity': item.quantity
                }
                if item.HasField("metadata"):
                    item_data['metadata'] = {
                        'type': item.metadata.type,
                        'value1': item.metadata.value1,
                        'value2': item.metadata.value2,
                        'value3': item.metadata.value3,
                        'flag': item.metadata.flag
                    }
                player_data['items'].append(item_data)
        
        result['player'] = player_data

    # Inventory Data (field2)
    if response_data.field2:
        inventory = response_data.field2
        inventory_data = {
            'item_id': inventory.item_id,
            'quantity': inventory.quantity,
            'encrypted_data': inventory.encrypted_data.hex() if inventory.encrypted_data else None,
            'inventory_type': inventory.inventory_type,
            'default_tab': inventory.default_tab,
            'timestamp': inventory.timestamp
        }
        
        # Inventory Entries
        if inventory.entries:
            inventory_data['entries'] = [{
                'item_type': entry.item_type,
                'count': entry.count
            } for entry in inventory.entries]
        
        result['inventory'] = inventory_data

    # Social Data (field6)
    if response_data.field6:
        social = response_data.field6
        result['social'] = {
            'social_id': social.social_id,
            'social_url': social.social_url,
            'associated_id': social.associated_id,
            'status': social.status,
            'privacy_level': social.privacy_level,
            'social_type': social.social_type
        }

    # Player Info (field7) - Additional player data
    if response_data.field7:
        player2 = response_data.field7
        result['player_additional'] = {
            'user_id': player2.user_id,
            'username': player2.username,
            'level': player2.level,
            'rank': player2.rank,
            'last_login': player2.last_login
        }

    # System Info (field8)
    if response_data.field8:
        system = response_data.field8
        result['system'] = {
            'os_type': system.os_type,
            'device_model': system.device_model,
            'platform': system.platform,
            'ram': system.ram,
            'storage': system.storage,
            'network_type': system.network_type
        }

    # Title Data (field9)
    if response_data.field9:
        title = response_data.field9
        result['title'] = {
            'title_id': title.title_id,
            'title_text': title.title_text,
            'unlock_status': title.unlock_status
        }

    # Currency (field10)
    if response_data.field10:
        currency = response_data.field10
        result['currency'] = {
            'currency_type': currency.currency_type,
            'amount': currency.amount,
            'bonus': currency.bonus,
            'expiration': currency.expiration
        }

    # Season Info (field11)
    if response_data.field11:
        season = response_data.field11
        result['season'] = {
            'season_number': season.season_number,
            'current_tier': season.current_tier,
            'max_tier': season.max_tier,
            'season_end': season.season_end,
            'rewards_claimed': season.rewards_claimed
        }

    result['credit'] = '@Ujjaiwal'
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)