from flask import Flask, request, jsonify
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from GetPlayerPersonalShow_pb2 import GetPlayerPersonalShow
import urllib3
import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Credentials for IND
UID = "3959794891"
PASSWORD = "CBECEA7B0F13FD5A4A9075F5831089C286FD5CC791BE9A00EF734CEBC20AC756"

# JWT generate URL
JWT_URL = "https://team-ujjaiwal-jwt.vercel.app/token"

# SEARCH URL for IND
SEARCH_URL = "https://client.ind.freefiremobile.com/FuzzySearchAccountByName"

# API Key
API_KEY = "unbelievablekeysforujjaiwal"

def get_jwt(uid, password):
    try:
        params = {'uid': uid, 'password': password}
        response = requests.get(JWT_URL, params=params)
        if response.status_code == 200:
            jwt_data = response.json()
            return jwt_data.get("token")  
        return None
    except Exception as e:
        print(f"Error fetching JWT: {e}")
        return None

def encrypt_name(nickname):
    encoded = nickname.encode("utf-8")
    proto_hex = "0a" + format(len(encoded), '02x') + encoded.hex()
    key = bytes([89, 103, 38, 116, 99, 37, 68, 69, 117, 104, 54, 37, 90, 99, 94, 56])
    iv = bytes([54, 111, 121, 90, 68, 114, 50, 50, 69, 51, 121, 99, 104, 106, 77, 37])
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pad(bytes.fromhex(proto_hex), AES.block_size)).hex()

def convert_timestamp(ts):
    try:
        dt = datetime.datetime.utcfromtimestamp(ts) + datetime.timedelta(hours=8)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(ts)

def format_player(player):
    player_info = {
        "accountId": str(player.user_id),
        "nickname": player.username,
        "level": player.level,
        "exp": player.experience,
        "rank": player.rank,
        "rankingPoints": player.skill_rating,
        "badgeId": player.title_id,
        "currentRank": player.current_rank,
        "countryCode": player.country_code,
        "clanId": str(player.clan_id),
        "clanTag": player.clan_tag,
        "matchesPlayed": player.matches_played,
        "kills": player.kills,
        "dailyChallenges": player.daily_challenges,
        "currentAvatar": player.current_avatar,
        "mainWeapon": player.main_weapon,
        "cosmeticSkin": player.cosmetic_skin,
        "lastLogin": convert_timestamp(player.last_login),
        "joinDate": convert_timestamp(player.join_date),
        "accountStatus": player.account_status,
        "emailVerified": player.email_verified,
        "phoneVerified": player.phone_verified,
        "gameVersion": player.game_version,
        "headshotPercentage": player.headshot_percentage,
        "encryptedStats": player.encrypted_stats.hex() if player.encrypted_stats else None
    }

    # Add subscription info if available
    if player.HasField('subscription'):
        player_info["subscription"] = {
            "tier": player.subscription.tier,
            "renewalPeriod": player.subscription.renewal_period
        }

    return player_info

def format_clan(clan):
    return {
        "clanId": clan.clan_id,
        "memberCount": clan.member_count,
        "clanLogo": clan.clan_logo.hex() if clan.clan_logo else None,
        "status": clan.status,
        "permissionLevel": clan.permission_level,
        "creationDate": convert_timestamp(clan.creation_date)
    }

@app.route('/search', methods=['GET'])
def search_by_name():
    name = request.args.get('nickname')
    key = request.args.get('key')

    if not name:
        return jsonify({"error": "Missing 'nickname' parameter"}), 400
    
    if key != API_KEY:
        return jsonify({"error": "Invalid API key"}), 401

    jwt_token = get_jwt(UID, PASSWORD)
    if not jwt_token:
        return jsonify({"error": "Failed to generate JWT"}), 500

    encrypted_data = encrypt_name(name)

    headers = {
        'X-Unity-Version': '2018.4.11f1',
        'ReleaseVersion': 'OB49',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-GA': 'v1 1',
        'Authorization': f'Bearer {jwt_token}',
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 7.1.2; ASUS_Z01QD Build/QKQ1.190825.002)',
        'Host': SEARCH_URL.split("//")[1].split("/")[0],
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip'
    }

    try:
        response = requests.post(SEARCH_URL, headers=headers, data=bytes.fromhex(encrypted_data), verify=False)
    except Exception as e:
        return jsonify({"error": f"Request error: {str(e)}"}), 500

    if response.status_code == 200 and response.content:
        player_data = GetPlayerPersonalShow()
        player_data.ParseFromString(response.content)

        result = {
            "Credit": "@Ujjaiwal",
            "players": [],
            "clans": [],
            "detailedPlayer": None,
            "currencies": []
        }

        # Format players
        for player in player_data.players:
            result["players"].append(format_player(player))

        # Format clans
        for clan in player_data.clans:
            result["clans"].append(format_clan(clan))

        # Detailed player if available
        if player_data.HasField('detailed_player'):
            result["detailedPlayer"] = format_player(player_data.detailed_player)

        # Currencies
        for currency in player_data.currencies:
            result["currencies"].append({
                "currencyType": currency.currency_type,
                "amount": currency.amount,
                "maxCapacity": currency.max_capacity,
                "bonus": currency.bonus
            })

        return jsonify(result)

    else:
        return jsonify({"error": "Failed to fetch data or empty response"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)