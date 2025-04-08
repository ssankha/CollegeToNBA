import requests
import json
import pandas as pd
import string
from bs4 import BeautifulSoup
import time

def get_all_players_base_info(output_file='players_base_info.json'):
    lowercase_alphabet = list(string.ascii_lowercase)

    ALPHABET_URL = 'https://www.basketball-reference.com/players/{}/'

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    })

    players = []
    for letter in lowercase_alphabet:
        letter_url = ALPHABET_URL.format(letter)
        letter_response = session.get(letter_url)
        
        print(letter_url)
        
        if letter_response.status_code == 200:
            soup = BeautifulSoup(letter_response.content, "html.parser")
            # Parse player data
            for row in soup.select("tbody tr"):
                player = {}
                
                # Extract fields based on `data-stat` attribute
                name = row.select_one("th[data-stat='player']")
                start_year = row.select_one("td[data-stat='year_min']")
                end_year = row.select_one("td[data-stat='year_max']")
                birth_date = row.select_one("td[data-stat='birth_date']")
                colleges = row.select_one("td[data-stat='colleges']")

                # Store data if available
                if name and start_year and end_year and birth_date and colleges:
                    player['name'] = name.get_text(strip=True)
                    player['start_year'] = start_year.get_text(strip=True)
                    player['end_year'] = end_year.get_text(strip=True)
                    player['birth_date'] = birth_date.get_text(strip=True)
                    player['colleges'] =  [college.strip() for college in colleges.get_text(", ", strip=True).split(",") if college.strip()]
                    
                    link = name.find("a")
                    if link:
                        player['profile_url'] = f"https://www.basketball-reference.com{link['href']}"

                    players.append(player)

                
            time.sleep(10)
        else:
            print("Request failed (Status Code:"  + str(letter_response.status_code) + ")")

    # Convert to JSON
    with open(output_file, 'w') as file:
        json.dump(players, file)
      

def get_player_info(input_file='players_base_info.json', output_file='player_detail_info.json'):
    with open(input_file, 'r') as file:
        all_player_json = json.load(file)
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
    })
    
    res = []
    try:
        for player_json in all_player_json:
            player_url = player_json['profile_url']
            print("Now processing: " + player_url)
            player_info_response = session.get(player_url)
            if player_info_response.status_code == 200:
                player_data = parse_player_webpage(player_info_response)
                res.append(player_data)

            time.sleep(10)
    except KeyboardInterrupt:
        with open(output_file, 'w') as file:
            json.dump(res, file)
    
    with open(output_file, 'w') as file:
        json.dump(res, file)
             

def parse_player_webpage(player_info_response):
    soup = BeautifulSoup(player_info_response.content, 'html.parser')
    
    player_data = {}
    # Extract Player's Name
    player_data['name'] = soup.find('h1').find('span').get_text(strip=True)

    # Extract Accolades (bling tags)
    accolades_section = soup.select('#bling li')
    accolades = [accolade.get_text(strip=True) for accolade in accolades_section]
    player_data['accolades'] = accolades if accolades else []

    # Extract Nicknames
    nickname_tag = soup.find('p', string=lambda text: text and '(' in text)
    if nickname_tag:
        nicknames = nickname_tag.get_text(strip=True)
        start = nicknames.find('(') + 1
        end = nicknames.find(')')
        nickname_list = nicknames[start:end].split(', ')
        player_data['nicknames'] = [nickname.strip() for nickname in nickname_list]
    else:
        player_data['nicknames'] = []

    # Find the paragraph containing height and weight, looking for the specific structure
    height_weight_spans = soup.select('div#meta p span')

    # Filter for height and weight values based on the patterns "7-2" and "225lb"
    height = None
    weight = None
    for span in height_weight_spans:
        text = span.get_text(strip=True)
        if '-' in text:  # Assuming height format like "7-2"
            height = text
        elif 'lb' in text:  # Assuming weight format like "225lb"
            weight = text

    player_data['height'] = height
    player_data['weight'] = weight
    
    # Extract Position
    position_paragraph = soup.find('strong', string=lambda t: t and "Position:" in t)
    if position_paragraph:
        s = position_paragraph.parent.contents[2].strip()
        position = [line.strip() for line in s.splitlines() if line.strip() and line.strip() != '▪'][0]
        player_data['position'] = position
        
    # Extract Teams and Years from Career Summary Table
    teams_and_years = []
    career_table = soup.find('table', {'id': 'totals'})
    if career_table:
        for row in career_table.select('tbody tr'):
            team_name = row.find('td', {'data-stat': 'team_id'}).get_text(strip=True)
            years = row.find('th', {'data-stat': 'season'}).get_text(strip=True)
            teams_and_years.append({'team': team_name, 'years': years})
    player_data['teams'] = teams_and_years

    # Extract Season Stats from Per Game Stats Table
    season_stats = []
    per_game_table = soup.find('table', {'id': 'per_game_stats'})
    if per_game_table:
        for season_row in per_game_table.select('tbody tr'):
            season_data = {col['data-stat']: col.get_text(strip=True) for col in season_row.find_all('td')}
            season_data['season'] = season_row.find('th', {'data-stat': 'year_id'}).get_text(strip=True)
            season_stats.append(season_data)
    player_data['season_stats'] = season_stats

    # Extract Career Stats from footer row
    career_stats = {}
    career_stats_row = per_game_table.select_one('tfoot tr')
    if career_stats_row:
        career_stats = {col['data-stat']: col.get_text(strip=True) for col in career_stats_row.find_all('td')}
    player_data['career_stats'] = career_stats
    
    return player_data

    

#get_all_players()
get_player_info()