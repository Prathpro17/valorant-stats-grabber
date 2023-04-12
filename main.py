import base64
import os
import time

import httpx
import urllib3

from rich.console import Console
from rich.table import Table

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


number_to_ranks = {
    0: "Unranked",
    1: "Unranked",
    2: "Unused 1",
    3: "Iron 1",
    4: "Iron 2",
    5: "Iron 3",
    6: "Bronze 1",
    7: "Bronze 2",
    8: "Bronze 3",
    9: "Silver 1",
    10: "Silver 2",
    11: "Silver 3",
    12: "Gold 1",
    13: "Gold 2",
    14: "Gold 3",
    15: "Platinum 1",
    16: "Platinum 2",
    17: "Platinum 3",
    18: "Diamond 1",
    19: "Diamond 2",
    20: "Diamond 3",
    21: "Immortal 1",
    22: "Immortal 2",
    23: "Immortal 3",   
    24: "Radiant"
}


region = 'ap'
glz_url = f"https://glz-{region}-1.{region}.a.pvp.net"
pd_url = f"https://pd.{region}.a.pvp.net"
henrik_url = "https://api.henrikdev.xyz"
headers = {}


def get_lockfile():
    try:
        with open(os.path.join(os.getenv('LOCALAPPDATA'), R'Riot Games\Riot Client\Config\lockfile')) as lockfile:
            data = lockfile.read().split(':')
            keys = ['name', 'PID', 'port', 'password', 'protocol']
            return dict(zip(keys, data))
    except:
        raise Exception("Lockfile not found")


lockfile = get_lockfile()


def get_current_version():
    data = httpx.get('https://valorant-api.com/v1/version')
    data = data.json()['data']
    version = f"{data['branch']}-shipping-{data['buildVersion']}-{data['version'].split('.')[3]}"
    return version


def get_headers():
    global headers
    if headers == {}:
        local_headers = {}
        local_headers['Authorization'] = 'Basic ' + base64.b64encode(('riot:' + lockfile['password']).encode()).decode()
        response = httpx.get(
            f"https://127.0.0.1:{lockfile['port']}/entitlements/v1/token",
            headers = local_headers,
            verify = False
        )
        entitlements = response.json()
        headers = {
            'Authorization': f"Bearer {entitlements['accessToken']}",
            'X-Riot-Entitlements-JWT': entitlements['token'],
            'X-Riot-ClientPlatform': "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
            'X-Riot-ClientVersion': get_current_version()
        }
    return headers


def get_self_puuid():
    local_headers = {}
    local_headers['Authorization'] = 'Basic ' + base64.b64encode(('riot:' + lockfile['password']).encode()).decode()
    response = httpx.get(
        f"https://127.0.0.1:{lockfile['port']}/entitlements/v1/token",
        headers = local_headers,
        verify = False
    )
    entitlements = response.json()
    puuid = entitlements['subject']
    return puuid


def get_name_from_puuid(puuid):
    response = httpx.put(
        pd_url + f"/name-service/v2/players",
        headers = get_headers(),
        json = [puuid],
        verify = False
    ).json()
    return {
        'username': response[0]["GameName"],
        'tag': response[0]["TagLine"],
        'full': f"{response[0]['GameName']}#{response[0]['TagLine']}"
    }


def get_hs_and_kd(puuid):
    hs_and_kd = {}
    matches = httpx.get(
        henrik_url + f"/valorant/v3/by-puuid/matches/{region}/{puuid}",
        params = { 'filter': 'competitive' },
        verify = False
    )
    hits = 0
    headshots = 0
    kills = 0
    deaths = 0
    for match in matches.json()['data']:
        for player in match['players']['all_players']:
            if player['puuid'] == puuid:
                hits += player['stats']['legshots']
                hits += player['stats']['bodyshots']
                hits += player['stats']['headshots']
                headshots += player['stats']['headshots']
                kills += player['stats']['kills']
                deaths += player['stats']['deaths']
    hs_and_kd['hs'] = f"{int((headshots / hits) * 100)}%"
    hs_and_kd['kd'] = round(kills / deaths, 2)
    return hs_and_kd


def get_player_stats(puuid):
    key_order = ['name', 'current_rank', 'peak_rank_with_act', 'hs', 'kd', 'level']
    player = {}
    playerName = get_name_from_puuid(puuid)
    player['name'] = playerName['full']
    resp1 = httpx.get(
        henrik_url + f"/valorant/v1/account/{playerName['username']}/{playerName['tag']}",
        verify = False
    ).json()
    player['level'] = resp1['data']['account_level']
    resp2 = httpx.get(
        henrik_url + f"/valorant/v2/by-puuid/mmr/{region}/{puuid}",
        verify = False
    ).json()
    player['current_rank'] = resp2['data']['current_data']['currenttierpatched']
    # player['peak_rank'] = resp2['data']['highest_rank']['patched_tier']
    player['peak_rank_with_act'] = f"{resp2['data']['highest_rank']['patched_tier']} ({resp2['data']['highest_rank']['season']})"
    hs_and_kd = get_hs_and_kd(puuid)
    player.update(hs_and_kd)
    return {k: player[k] for k in key_order}


def get_party_members_puuids():
    partyID = httpx.get(
        glz_url + f"/parties/v1/players/{get_self_puuid()}",
        headers = get_headers(),
        verify = False
    ).json()
    response = httpx.get(
        glz_url + f"/parties/v1/parties/{partyID['CurrentPartyID']}",
        headers = get_headers(),
        verify = False
    ).json()
    #regex = f"aresriot.*{region}-gp-"
    member_puuids = []
    for member in response['Members']:
        member_puuids.append(member['Subject'].lower())
    return member_puuids


def addTableColumn(cols: list):
    for col in cols:
        table.add_column(col, justify = 'center')




if __name__ == '__main__':

    # os.system('cls')

    table = Table(title = 'Party')

    addTableColumn(['Name', 'Current Rank', 'Peak Rank', 'HS', 'KD', 'Level'])

    for index, player_puuid in enumerate(get_party_members_puuids()):
        print(f"Fetching player {index + 1}...", end = '\r')
        table.add_row(*[str(attr) for attr in get_player_stats(player_puuid).values()])
        print(end = '\x1b[2K')    
        print('Done.', end = '\r')
        time.sleep(0.1)
        print(end = '\x1b[2K')

    print()
    console = Console()
    console.print(table, justify = 'center')
    console.print('(HS and KD are an average of the last 5 competitive matches the player has played)', justify = 'center')
