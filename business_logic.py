from bs4 import BeautifulSoup
from urllib.parse import quote


def parse_html(html_content: str):
    soup = BeautifulSoup(html_content, "lxml")
    battle_summary = {
        "battle_map": "",
        "time_stamp": "",
        "match_duration": "",
        "description": "",
        "team_1": [],
        "team_2": [],
        "session_id": "",
        "war_thunder_server_replay_url": "https://warthunder.com/en/tournament/replay"
    }

    try:
        header = soup.select_one("div._resultsItem__header_1umbu_355")
        if header:
            battle_summary["battle_map"] = (
                    header.select_one("div._resultsItem__headerTitle_1umbu_366") or BeautifulSoup("", "lxml")
            ).text.strip()

            battle_summary["time_stamp"] = (
                    header.select_one("span._resultsItem__eventTime_1umbu_412") or BeautifulSoup("", "lxml")
            ).text.strip()

            battle_summary["match_duration"] = (
                    header.select_one("span._resultsItem__eventDuration_1umbu_415") or BeautifulSoup("", "lxml")
            ).text.strip()

            battle_summary["description"] = (
                    header.select_one("div._resultsItem__headerLead_1umbu_376") or BeautifulSoup("", "lxml")
            ).text.strip()

    except Exception as e:
        print(f"Error parsing header: {e}")

    try:
        teams = soup.select("div._resultItemNames_1umbu_219")
        team_int = 1
        for team in teams:
            team_name_tag = team.select_one("div._resultItemNames__title_1umbu_223")
            team_name = team_name_tag.text.strip() if team_name_tag else f"Team {team_int}"

            players = team.select("li._resultItemNames__item_1umbu_237")
            for player in players:
                try:
                    name_tag = player.select_one("div._resultItemNames__name_1umbu_246 a")
                    id_tag = player.select_one("div._resultItemNames__nameId_1umbu_259")

                    if name_tag and id_tag:
                        name = name_tag.text.strip()
                        encoded_name = quote(name)
                        player_url = f"https://warthunder.com/en/community/userinfo/?nick={encoded_name}"
                        player_id = id_tag.text.strip().replace("ID ", "")

                        if team_int == 1:
                            battle_summary["team_1"].append([player_id, name, player_url])
                        else:
                            battle_summary["team_2"].append([player_id, name, player_url])
                except Exception as pe:
                    print(f"Error parsing player: {pe}")

            team_int = 2  # assumes there are only two teams

    except Exception as e:
        print(f"Error parsing teams: {e}")

    try:
        session_div = soup.find('div', class_=lambda x: x and "_resultsItem__sessionId" in x)
        if session_div:
            lines = session_div.get_text(separator="\n").split("\n")
            for line in lines:
                line = line.strip()
                if len(line) == 15:
                    battle_summary["session_id"] = line
                    break
    except Exception as e:
        print(f"Error parsing session ID: {e}")

    return battle_summary


if __name__ == "__main__":
    try:
        with open("html.txt", "r", encoding="utf-8") as file:
            html_tree: str = file.read()
            result = parse_html(html_tree)
            print(result)
    except FileNotFoundError:
        print("The file 'html.txt' was not found.")
    except Exception as e:
        print(f"An error occurred while reading the file or parsing HTML: {e}")
