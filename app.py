from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
from flask import Flask, request, jsonify
import requests
import random
import new_pb2
from secret import key, iv

app = Flask(__name__)

def hex_to_bytes(hex_string):
    return bytes.fromhex(hex_string)

def create_protobuf(player_id, region_code):
    # Create a FreeFirePlayer protobuf message
    message = new_pb2.FreeFirePlayer()
    
    # Set basic account info
    message.account.account_id = str(player_id)
    message.account.player_id = str(player_id)
    message.account.name = f"Player{player_id}"
    message.account.level = random.randint(1, 100)
    message.account.exp = random.randint(1000, 100000)
    message.account.region = region_code.upper()
    message.account.created_at = 1609459200  # Fixed timestamp
    message.account.last_login = 1672531200  # Recent timestamp
    message.account.season_id = 24
    message.account.has_elite_pass = random.choice([True, False])
    message.account.release_version = "OB49"
    message.account.is_prime_user = random.choice([True, False])
    message.account.prime_tier = random.randint(1, 3)
    
    # Set rank info
    for rank_field in [message.rank.battle_royale, message.rank.clash_squad, message.rank.legends_awakened]:
        rank_field.max_rank = 100
        rank_field.current_rank = random.randint(1, 100)
        rank_field.rank_points = random.randint(100, 5000)
        rank_field.is_visible = True
    
    # Set equipped items
    message.equipped.weapon_ids.extend([101, 205, 307])
    message.equipped.weapon_images.extend(["w101.png", "w205.png", "w307.png"])
    message.equipped.outfit_ids.extend([501, 602])
    message.equipped.outfit_images.extend(["o501.png", "o602.png"])
    message.equipped.skill_ids.extend([701, 802])
    message.equipped.skill_images.extend(["s701.png", "s802.png"])
    message.equipped.awakened_skill = 901
    message.equipped.pet_skill_boost = 2
    
    # Set weapon mastery
    weapons = [
        {"id": 101, "name": "M4A1"},
        {"id": 205, "name": "AK47"},
        {"id": 307, "name": "AWM"}
    ]
    for weapon in weapons:
        mastery = message.weapon_mastery.masteries.add()
        mastery.weapon_id = weapon["id"]
        mastery.level = random.randint(1, 100)
        mastery.mastery_badge = f"Gold {random.randint(1, 3)}"
        mastery.accuracy = round(random.uniform(10.0, 90.0), 1)
        mastery.kills = random.randint(10, 5000)
    message.weapon_mastery.overall_mastery_level = random.randint(1, 100)
    
    # Set guild info
    message.guild.guild_id = "g12345"
    message.guild.name = "Elite Squad"
    message.guild.level = random.randint(1, 30)
    message.guild.member_count = random.randint(5, 100)
    message.guild.capacity = 100
    message.guild.owner_id = "leader123"
    message.guild.guild_badge = "gold_badge"
    message.guild.guild_awakening_level = random.randint(1, 5)
    
    # Set pet info
    message.pet.pet_id = 1001
    message.pet.level = random.randint(1, 30)
    message.pet.exp = random.randint(100, 3000)
    message.pet.skin_id = 2001
    message.pet.selected_skill_id = 3001
    message.pet.is_selected = True
    message.pet.has_awakened_form = random.choice([True, False])
    message.pet.pet_rarity = random.randint(1, 3)
    
    # Set awakening progress
    message.awakening.awakening_level = random.randint(1, 5)
    message.awakening.unlocked_abilities.extend(["Double Heal", "Speed Boost"])
    message.awakening.fragments_collected = random.randint(10, 100)
    message.awakening.fragments_required = 100
    
    # Set social info
    message.social.signature = "Pro player looking for squad"
    message.social.language = "en"
    message.social.likes = random.randint(0, 10000)
    message.social.badge_count = random.randint(0, 20)
    message.social.is_content_creator = random.choice([True, False])
    message.social.ff_id = f"FF{player_id}"
    
    # Set credit score
    message.credit.score = random.randint(50, 100)
    message.credit.period_start = 1609459200
    message.credit.period_end = 1672531200
    message.credit.reward_state = random.randint(0, 3)
    message.credit.is_trusted_player = random.choice([True, False])
    
    return message.SerializeToString()

def protobuf_to_hex(protobuf_data):
    return binascii.hexlify(protobuf_data).decode()

def decode_hex(hex_string):
    byte_data = binascii.unhexlify(hex_string.replace(' ', ''))
    player_data = new_pb2.FreeFirePlayer()
    player_data.ParseFromString(byte_data)
    return player_data

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
        return "3942040791", "EDD92B8948F4453F544C9432DFB4996D02B4054379A0EE083D8459737C50800B"
    elif region in ["NA", "BR", "SAC", "US"]:
        return "uid", "password"
    else:
        return "uid", "password"

def get_jwt_token(region):
    uid, password = get_credentials(region)
    jwt_url = f"https://aditya-jwt-v9op.onrender.com/token?uid={uid}&password={password}"
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
        player_id = int(uid)
    except ValueError:
        return jsonify({"error": "Invalid UID"}), 400

    jwt_info = get_jwt_token(region)
    if not jwt_info or 'token' not in jwt_info:
        return jsonify({"error": "Failed to fetch JWT token"}), 500

    api = jwt_info['serverUrl']
    token = jwt_info['token']

    protobuf_data = create_protobuf(player_id, region)
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
        player_data = decode_hex(hex_response)
    except Exception as e:
        return jsonify({"error": f"Failed to parse Protobuf: {str(e)}"}), 500

    # Convert the FreeFirePlayer protobuf to a JSON response
    result = {
        'account': {
            'account_id': player_data.account.account_id,
            'player_id': player_data.account.player_id,
            'name': player_data.account.name,
            'level': player_data.account.level,
            'exp': player_data.account.exp,
            'region': player_data.account.region,
            'created_at': player_data.account.created_at,
            'last_login': player_data.account.last_login,
            'season_id': player_data.account.season_id,
            'has_elite_pass': player_data.account.has_elite_pass,
            'release_version': player_data.account.release_version,
            'is_prime_user': player_data.account.is_prime_user,
            'prime_tier': player_data.account.prime_tier
        },
        'rank': {
            'battle_royale': {
                'max_rank': player_data.rank.battle_royale.max_rank,
                'current_rank': player_data.rank.battle_royale.current_rank,
                'rank_points': player_data.rank.battle_royale.rank_points,
                'is_visible': player_data.rank.battle_royale.is_visible
            },
            'clash_squad': {
                'max_rank': player_data.rank.clash_squad.max_rank,
                'current_rank': player_data.rank.clash_squad.current_rank,
                'rank_points': player_data.rank.clash_squad.rank_points,
                'is_visible': player_data.rank.clash_squad.is_visible
            },
            'legends_awakened': {
                'max_rank': player_data.rank.legends_awakened.max_rank,
                'current_rank': player_data.rank.legends_awakened.current_rank,
                'rank_points': player_data.rank.legends_awakened.rank_points,
                'is_visible': player_data.rank.legends_awakened.is_visible
            }
        },
        'equipped': {
            'weapon_ids': list(player_data.equipped.weapon_ids),
            'weapon_images': list(player_data.equipped.weapon_images),
            'outfit_ids': list(player_data.equipped.outfit_ids),
            'outfit_images': list(player_data.equipped.outfit_images),
            'skill_ids': list(player_data.equipped.skill_ids),
            'skill_images': list(player_data.equipped.skill_images),
            'awakened_skill': player_data.equipped.awakened_skill,
            'pet_skill_boost': player_data.equipped.pet_skill_boost
        },
        'weapon_mastery': {
            'masteries': [{
                'weapon_id': m.weapon_id,
                'level': m.level,
                'mastery_badge': m.mastery_badge,
                'accuracy': m.accuracy,
                'kills': m.kills
            } for m in player_data.weapon_mastery.masteries],
            'overall_mastery_level': player_data.weapon_mastery.overall_mastery_level
        },
        'guild': {
            'guild_id': player_data.guild.guild_id,
            'name': player_data.guild.name,
            'level': player_data.guild.level,
            'member_count': player_data.guild.member_count,
            'capacity': player_data.guild.capacity,
            'owner_id': player_data.guild.owner_id,
            'guild_badge': player_data.guild.guild_badge,
            'guild_awakening_level': player_data.guild.guild_awakening_level
        },
        'pet': {
            'pet_id': player_data.pet.pet_id,
            'level': player_data.pet.level,
            'exp': player_data.pet.exp,
            'skin_id': player_data.pet.skin_id,
            'selected_skill_id': player_data.pet.selected_skill_id,
            'is_selected': player_data.pet.is_selected,
            'has_awakened_form': player_data.pet.has_awakened_form,
            'pet_rarity': player_data.pet.pet_rarity
        },
        'awakening': {
            'awakening_level': player_data.awakening.awakening_level,
            'unlocked_abilities': list(player_data.awakening.unlocked_abilities),
            'fragments_collected': player_data.awakening.fragments_collected,
            'fragments_required': player_data.awakening.fragments_required
        },
        'social': {
            'signature': player_data.social.signature,
            'language': player_data.social.language,
            'likes': player_data.social.likes,
            'badge_count': player_data.social.badge_count,
            'is_content_creator': player_data.social.is_content_creator,
            'ff_id': player_data.social.ff_id
        },
        'credit': {
            'score': player_data.credit.score,
            'period_start': player_data.credit.period_start,
            'period_end': player_data.credit.period_end,
            'reward_state': player_data.credit.reward_state,
            'is_trusted_player': player_data.credit.is_trusted_player
        },
        'credit': '@Ujjaiwal'
    }

    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)