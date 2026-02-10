import time
import json
import re
from urllib.parse import quote_plus
from threading import Lock
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64
from bs4 import BeautifulSoup

lock = Lock()

def rsa_encrypt_password(password: str, modulus_hex: str, exponent_hex: str) -> str:
    n = int(modulus_hex, 16)
    e = int(exponent_hex, 16)
    rsa_key = RSA.construct((n, e))
    cipher = PKCS1_v1_5.new(rsa_key)
    encrypted = cipher.encrypt(password.encode("utf-8"))
    return base64.b64encode(encrypted).decode()

def parse_account_page(html):
    balance = country = "none"
    if not html:
        return balance, country
    soup = BeautifulSoup(html, "html.parser")
    bal = soup.find("div", class_="accountData price")
    if bal:
        balance = bal.get_text(strip=True)
    m = re.search(r'countrycode":"([A-Z]{2})"', html, re.I)
    if m:
        country = m.group(1)
    return balance, country

def parse_profile_page(html):
    online = "none"
    comm_ban = "None"
    if not html:
        return online, comm_ban
    soup = BeautifulSoup(html, "html.parser")
    ingame = soup.find("div", class_="profile_in_game_name")
    if ingame:
        online = f"In-Game: {ingame.get_text(strip=True)}"
    elif "Last Online" in html:
        m = re.search(r'(Last\s+Online[^<]+)', html, re.I)
        if m:
            online = m.group(1)
    if "community banned" in html.lower():
        comm_ban = "Community Banned"
    if "permanently banned" in html.lower():
        comm_ban = "Permanently Banned"
    return online, comm_ban

def parse_games_page(html):
    limited = "none"
    games = []
    if not html:
        return limited, 0, games
    m = re.search(r'is_limited&quot;:(true|false)', html, re.I)
    if m:
        limited = m.group(1)
    games = re.findall(r';name&quot;:&quot;([^&]+)&quot;', html)
    games = [BeautifulSoup(g, "html.parser").get_text() for g in games]
    return limited, len(games), games

def parse_vac_page(html):
    vac_list = []
    gameban_list = []
    if not html:
        return vac_list, gameban_list
    soup = BeautifulSoup(html, "html.parser")
    for span in soup.find_all("span", class_="help_highlight_text"):
        txt = span.get_text(strip=True)
        if txt:
            vac_list.append(txt)
    if "game ban" in html.lower():
        gameban_list = re.findall(r'Game Bans.*?help_highlight_text">(.*?)</span>', html, re.I|re.S)
    return vac_list, gameban_list

def login_to_steam(username, password, client):
    headers = {
        "Accept": "*/*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://steamcommunity.com",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_5 like Mac OS X)",
        "Accept-Language": "en-us"
    }

    ts = str(int(time.time()))
    r = client.post(
        "https://steamcommunity.com/login/getrsakey/",
        data=f"donotcache={ts}&username={username}",
        headers=headers
    )
    rsa_data = r.json() if r.headers.get("content-type","").startswith("application/json") else None
    if not rsa_data or not rsa_data.get("success"):
        return False, None, None

    enc = rsa_encrypt_password(password, rsa_data["publickey_mod"], rsa_data["publickey_exp"])
    enc = quote_plus(enc)

    login_data = (
        f"donotcache={ts}&password={enc}&username={username}"
        "&twofactorcode=&emailauth=&loginfriendlyname=&captchagid=&captcha_text="
        f"&emailsteamid=&rsatimestamp={rsa_data['timestamp']}&remember_login=false"
        "&oauth_client_id=C1F110D6&mobile_chat_client=true"
    )

    r = client.post(
        "https://steamcommunity.com/login/dologin/",
        data=login_data,
        headers=headers
    )
    res = r.json() if r.headers.get("content-type","").startswith("application/json") else None
    if not res or not res.get("success"):
        return False, None, None

    steamid = None
    if res.get("oauth"):
        try:
            steamid = json.loads(res["oauth"]).get("steamid")
        except:
            pass
    if not steamid and isinstance(res.get("transfer_parameters"), dict):
        steamid = res["transfer_parameters"].get("steamid")
    if not steamid:
        return False, None, None

    acc = client.get("https://store.steampowered.com/account/", allow_redirects=False)
    acc_html = acc.text if acc.status_code == 200 else ""
    balance, country = parse_account_page(acc_html)

    prof = client.get(f"https://steamcommunity.com/profiles/{steamid}", allow_redirects=False)
    prof_html = prof.text if prof.status_code == 200 else ""
    online, comm_ban = parse_profile_page(prof_html)

    games = client.get(f"https://steamcommunity.com/profiles/{steamid}/games?tab=all", allow_redirects=False)
    games_html = games.text if games.status_code == 200 else ""
    limited, total_games, games_list = parse_games_page(games_html)

    vac = client.get("https://help.steampowered.com/en/wizard/VacBans", allow_redirects=False)
    vac_html = vac.text if vac.status_code == 200 else ""
    vac_list, gameban_list = parse_vac_page(vac_html)

    capture = {
        "Balance": balance,
        "Country": country,
        "Online": online,
        "CommunityBan": comm_ban,
        "Limited": limited,
        "TotalGames": total_games,
        "VAC": vac_list,
        "GameBans": gameban_list,
        "SteamGuard": "Enabled" if client.cookies.get("steamLoginSecure") else "Unknown"
    }
    return True, steamid, capture

if __name__ == "__main__":
    user_input = input("Enter user:pass => ")
    username, password = user_input.split(":", 1)

    client = requests.Session()
    ok, steamid, data = login_to_steam(username.strip(), password.strip(), client)

    if ok:
        print("[✅] Login Success")
        for k, v in data.items():
            print(f"{k}: {v}")
    else:
        print("Login failed")
