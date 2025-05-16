from bs4 import BeautifulSoup
from urllib.parse import quote


def parse_html(html_content: str):
    soup = BeautifulSoup(html_content, "lxml")
    battle_summary = {}
    # Extract main header details
    header = soup.select_one("div._resultsItem__header_1umbu_355")
    battle_map: str = header.select_one("div._resultsItem__headerTitle_1umbu_366").text.strip()
    time: str = header.select_one("span._resultsItem__eventTime_1umbu_412").text.strip()
    duration: str = header.select_one("span._resultsItem__eventDuration_1umbu_415").text.strip()
    description: str = header.select_one("div._resultsItem__headerLead_1umbu_376").text.strip()

    team_1: list = []
    team_2: list = []
    session_id: str = ""
    # Extract teams and players
    teams = soup.select("div._resultItemNames_1umbu_219")
    team_int = 1
    for team in teams:
        team_name = team.select_one("div._resultItemNames__title_1umbu_223").text.strip()
        # print(f"\n{team_name}")
        players = team.select("li._resultItemNames__item_1umbu_237")
        for player in players:
            name = player.select_one("div._resultItemNames__name_1umbu_246 a").text.strip()
            encoded_name = quote(name)
            player_url = f"https://warthunder.com/en/community/userinfo/?nick={encoded_name}"
            player_id = player.select_one("div._resultItemNames__nameId_1umbu_259").text.strip()
            # print(f"  - {name} ({player_url})")
            if team_int == 1:
                team_1.append([player_id.replace("ID ", ""), name, player_url])
            else:
                team_2.append([player_id.replace("ID ", ""), name, player_url])
        team_int = 2

    # Get Session ID
    session_div = soup.find('div', class_=lambda x: x and "_resultsItem__sessionId" in x)
    if session_div:
        lines = session_div.get_text(separator="\n").split("\n")
        for line in lines:
            line = line.strip()
            if len(line) == 15:  # length of session ID
                session_id = line
                # print("Session ID:", session_id)

    # print("Match Title:", battle_map)
    # print("Time:", time)
    # print("Duration:", duration)
    # print("Description:", description)
    battle_summary = {
        "battle_map": battle_map,
        "time_stamp": time,
        "match_duration": duration,
        "description": description,
        "team_1": team_1,
        "team_2": team_2,
        "session_id": session_id,
        "war_thunder_server_replay_url": "https://warthunder.com/en/tournament/replay"
    }
    return battle_summary


if __name__ == "__main__":
    with open("html.txt", "r", encoding="utf-8") as file:
        html_tree: str = file.read()
        print(parse_html(html_tree))
