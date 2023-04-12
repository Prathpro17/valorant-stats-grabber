import base64
import os

import httpx
import urllib3

from rich.console import Console
from rich.table import Table
from rich.align import Align

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


def get_puuid():
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


def get_hs(member):
    player = {}
    hs_resp1 = httpx.get(
        pd_url + f"/mmr/v1/players/{get_puuid()}/competitiveupdates",
        headers = get_headers(),
        params = { 'startIndex': 0, 'endIndex': 1, 'queue': 'competitive'},
        verify = False
    )
    try:
        hs_resp = httpx.get(
            pd_url + f"/match-details/v1/matches/{hs_resp1.json()['Matches'][0]['MatchID']}",
            headers = get_headers(),
            verify = False
        )
        if hs_resp.status_code == 404:
            player['kd'] = "N/a"
            player['hs'] = "N/a"
            return player
        total_hits = 0
        total_headshots = 0
        for rround in hs_resp.json()["roundResults"]:
            for p in rround["playerStats"]:
                if p["subject"] == get_puuid():
                    for hits in p["damage"]:
                        total_hits += hits["legshots"]
                        total_hits += hits["bodyshots"]
                        total_hits += hits["headshots"]
                        total_headshots += hits["headshots"]
        for p in hs_resp.json()["players"]:
            if p["subject"] == get_puuid():
                kills = p["stats"]["kills"]
                deaths = p["stats"]["deaths"]
        if deaths == 0:
            kd = kills
        elif kills == 0:
            kd = 0
        else:
            kd = round(kills/deaths, 2)
        player['kd'] = kd
        player['hs'] = "N/a"
        if total_hits == 0:
            return player
        player['hs'] = f"{int((total_headshots/total_hits)*100)}%"
        return player
    except KeyError:
        return {'kd': 'N/a', 'hs': 'N/a'}


def get_act_from_id(actId):
    response = httpx.get(
        f"https://shared.{region}.a.pvp.net/content-service/v3/content",
        headers = get_headers(),
        verify = False
    ).json()
    act = None
    episode = None
    act_found = False
    for season in response["Seasons"]:
        if season["ID"].lower() == actId.lower():
            act = int(season["Name"][-1])
            act_found = True
        if act_found and season["Type"] == "episode":
            episode = int(season["Name"][-1])
            break
    return f"e{episode}a{act}"


def get_player_stats(member):
    key_order = ['name', 'current_rank', 'peak_rank_with_act', 'hs', 'kd', 'level']
    player = {}
    player['name'] = get_name_from_puuid(member['Subject'])['full']
    player['level'] = member['PlayerIdentity']['AccountLevel']
    response = httpx.get(
        pd_url + f"/mmr/v1/players/{member['Subject']}",
        headers = get_headers(),
        verify = False
    ).json()
    try:
        rank = None
        max_rank = None
        max_rank_act = None
        for act in response['QueueSkills']['competitive']['SeasonalInfoBySeasonID']:
            get_act_from_id(act)
            competitiveTier = response['QueueSkills']['competitive']['SeasonalInfoBySeasonID'][act]['CompetitiveTier']
            rankIndex = response['QueueSkills']['competitive']['SeasonalInfoBySeasonID'][act]['Rank']
            act_rank = max(competitiveTier, rankIndex)
            if rank is None:
                rank = act_rank
                max_rank_act = get_act_from_id(act)
            elif act_rank > rank:
                if max_rank is None or act_rank > max_rank:
                    max_rank = act_rank
                    max_rank_act = get_act_from_id(act)
            player['current_rank'] = number_to_ranks[rank]
            try:
                player['peak_rank'] = number_to_ranks[max_rank]
            except KeyError:
                player['peak_rank'] = number_to_ranks[rank]
            player['peak_rank_act'] = max_rank_act
            player['peak_rank_with_act'] = f"{player['peak_rank']} ({max_rank_act})"
    except TypeError:
        player['current_rank'] = 'Unranked'
        player['peak_rank'] = 'Unranked'
    hsAndKd = get_hs(member)
    player['hs'] = hsAndKd['hs']
    player['kd'] = hsAndKd['kd']
    return {k: player[k] for k in key_order}


def get_party_members():
    partyID = httpx.get(
        glz_url + f"/parties/v1/players/{get_puuid()}",
        headers = get_headers(),
        verify = False
    ).json()
    response = httpx.get(
        glz_url + f"/parties/v1/parties/{partyID['CurrentPartyID']}",
        headers = get_headers(),
        verify = False
    ).json()
    #regex = f"aresriot.*{region}-gp-"
    return_data = []
    for member in response['Members']:
        return_data.append(get_player_stats(member))
    return return_data



table = Table(title='Party')

table.add_column('Name', justify = 'center')
table.add_column('Current Rank', justify = 'center')
table.add_column('Peak Rank', justify = 'center')
table.add_column('HS', justify = 'center')
table.add_column('KD', justify = 'center')
table.add_column('Level', justify = 'center')

players = get_party_members()
for player in players:
    table.add_row(*[str(attr) for attr in player.values()])

print()
console = Console()
console.print(table, justify = 'center')
console.print('(HS and KD are of the last competitive match the player has played)', justify = 'center')