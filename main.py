import base64
import os

import requests
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
    data = requests.get('https://valorant-api.com/v1/version')
    data = data.json()['data']
    version = f"{data['branch']}-shipping-{data['buildVersion']}-{data['version'].split('.')[3]}"
    return version


def get_headers():
    global headers
    if headers == {}:
        local_headers = {}
        local_headers['Authorization'] = 'Basic ' + base64.b64encode(('riot:' + lockfile['password']).encode()).decode()
        response = requests.get(
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
    response = requests.get(
        f"https://127.0.0.1:{lockfile['port']}/entitlements/v1/token",
        headers = local_headers,
        verify = False
    )
    entitlements = response.json()
    puuid = entitlements['subject']
    return puuid


def get_name_from_puuid(puuid):
    response = requests.put(
        pd_url + f"/name-service/v2/players",
        headers = get_headers(),
        json= [puuid],
        verify = False
    ).json()
    return {
        'username': response[0]["GameName"],
        'tag': response[0]["TagLine"],
        'full': f"{response[0]['GameName']}#{response[0]['TagLine']}"
    }


def get_player_stats(member):
    key_order = ['name', 'current_rank', 'peak_rank', 'level']
    player = {}
    player['name'] = get_name_from_puuid(member['Subject'])['full']
    player['level'] = member['PlayerIdentity']['AccountLevel']
    response = requests.get(
        pd_url + f"/mmr/v1/players/{member['Subject']}",
        headers = get_headers(),
        verify = False
    ).json()
    try:
        rank = None
        max_rank = None
        for act in response['QueueSkills']['competitive']['SeasonalInfoBySeasonID']:
            competitiveTier = response['QueueSkills']['competitive']['SeasonalInfoBySeasonID'][act]['CompetitiveTier']
            rankIndex = response['QueueSkills']['competitive']['SeasonalInfoBySeasonID'][act]['Rank']
            act_rank = max(competitiveTier, rankIndex)
            if rank is None:
                rank = act_rank
            elif act_rank > rank:
                if max_rank is None or act_rank > max_rank:
                    max_rank = act_rank
            player['current_rank'] = number_to_ranks[rank]
            try:
                player['peak_rank'] = number_to_ranks[max_rank]
            except KeyError:
                player['peak_rank'] = rank
    except TypeError:
        player['current_rank'] = 'Unranked'
        player['peak_rank'] = 'Unranked'
    return {k: player[k] for k in key_order}


def get_party_members():
    partyID = requests.get(
        glz_url + f"/parties/v1/players/{get_puuid()}",
        headers = get_headers(),
        verify = False
    ).json()
    response = requests.get(
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

table.add_column('Name')
table.add_column('Current Rank')
table.add_column('Peak Rank')
table.add_column('Level')

players = get_party_members()
for player in players:
    table.add_row(*[str(attr) for attr in player.values()])

print()
console = Console()
console.print(table)