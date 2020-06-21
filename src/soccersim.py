import os
import random
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import math
from enum import Enum

clear = lambda: os.system('clear')

class Position(Enum):
    DEF = 0
    MID = 1
    ATK = 2
    GK = 3

battle_layers = [(Position.MID, Position.MID), (Position.ATK, Position.DEF), (Position.ATK, Position.GK)]
positions = {'Golman':Position.GK, 'Branič':Position.DEF, 'Veznjak':Position.MID, 'Napadač':Position.ATK}

class Player:
    def __init__(self, name, age, ovr, pot, pos, awr, dwr):
        self.name = name
        self.age = age
        self.ovr = ovr/10
        self.pot = pot/10
        self.position = positions[pos]
        self.exp = (age-17)/18 #average retirement at 35y
        if self.exp>1: self.exp = 1

        self.skill = (1+0.1*self.exp)*(1.5*self.ovr+0.5*self.pot)/2
        wr = {'High': 1, 'Medium': 0.95, 'Low': 0.9}
        self.k_awr = wr[awr]
        self.k_dwr = wr[dwr]
        self.n_atk_decays = 0
        self.atk_decay = self.k_awr*age/100
        self.n_def_decays = 0
        self.def_decay = self.k_dwr*age/100

    def current_skill(self, atk):
        current_skill = self.skill - (self.n_atk_decays * self.atk_decay + self.n_def_decays * self.def_decay)
        if atk:
            current_skill *= self.k_awr
            #self.n_atk_decays += 1
        else:
            current_skill *= self.k_dwr
            #self.n_def_decays += 1
        return current_skill

    def refill_skill(self, refill_percent):
        self.n_atk_decays -= int(round(refill_percent * self.n_atk_decays))
        self.n_def_decays -= int(round(refill_percent * self.n_def_decays))

class Team:
    def __init__(self, players):
        self.goals = 0
        self.dma_players = [[],[],[]] #def mid attack players
        self.goalkeeper = None
        for player in players:
            if player.position != Position.GK:
                self.dma_players[player.position.value].append(player)
            else: self.goalkeeper = player

    def layer_strength(self, position, atk):
        layer_strength = 0
        if position != Position.GK:
            for player in self.dma_players[position.value]:
                layer_strength += player.current_skill(atk)
            x = Position.MID.value-position.value
            if x != 0:
                for player in self.dma_players[position.value+x]:
                    layer_strength += 0.5*player.current_skill(atk)
        else: layer_strength = self.goalkeeper.current_skill(atk)
        return layer_strength

    def refill_players_skill(self, refill_percent):
        self.goalkeeper.refill_skill(refill_percent)
        for group in self.dma_players:
            for player in group:
                player.refill_skill(refill_percent)

class Match:
    def __init__(self, home_team, away_team):
        self.home_team = home_team
        self.away_team = away_team

    # k = shape, lmb = rate
    def erlang(self, x, k, lmb):
        sum = 0
        for n in range(k):
            sum += math.exp(-lmb * x) * (lmb * x) ** n / math.factorial(n)
        return 1 - sum

    def erlang_decision(self, layer_skill1, layer_skill2, layer_ff1, layer_ff2):
        if layer_skill1 <= 10:
            layer_skill1 *= 4.5
        if layer_skill2 <= 10:
            layer_skill2 *= 4.5

        vatk = math.floor((layer_skill1 - (layer_skill1 - layer_skill2)/5) * self.erlang(random.random() * layer_skill1, 3, 0.25))
        vdef = math.ceil((layer_skill2 - (layer_skill2 - layer_skill1)/5) * self.erlang(random.random() * layer_skill2, 3, 0.25))
        return vatk > vdef+0.2*layer_skill2

    def simulate(self, n_matches, atk_per_team):
        print("Home Skill")
        print("GK: {}".format(self.home_team.layer_strength(Position.GK, False)))
        print("DEF: {}".format(self.home_team.layer_strength(Position.DEF, False)))
        print("MID: {}".format(self.home_team.layer_strength(Position.MID, True)))
        print("ATK: {}".format(self.home_team.layer_strength(Position.ATK, True)))
        print("\n")
        print("Away Skill")
        print("GK: {}".format(self.away_team.layer_strength(Position.GK, False)))
        print("DEF: {}".format(self.away_team.layer_strength(Position.DEF, False)))
        print("MID: {}".format(self.away_team.layer_strength(Position.MID, True)))
        print("ATK: {}".format(self.away_team.layer_strength(Position.ATK, True)))
        print("\n")

        results = {}
        home_draw_away = [0,0,0]
        scored_goals = [0,0]

        for i in range(n_matches):
            self.home_team.goals = 0
            self.away_team.goals = 0
            self.home_team.refill_players_skill(1)
            self.away_team.refill_players_skill(1)

            for j in range(atk_per_team):
                if j==int(round(atk_per_team/2)):
                    self.home_team.refill_players_skill(0.5)
                    self.away_team.refill_players_skill(0.5)
                for k in range(2):
                    atk_team = self.home_team if k==0 else self.away_team
                    def_team = self.home_team if k == 1 else self.away_team
                    for battle_layer in battle_layers:
                        atk_team_layer_strength = atk_team.layer_strength(battle_layer[0], True)
                        def_team_layer_strength = def_team.layer_strength(battle_layer[1], False)
                        if battle_layer[1] == Position.GK:
                            atk_team_layer_strength /= (len(atk_team.dma_players[2]) + 0.5*len(atk_team.dma_players[1]))
                        if self.erlang_decision(atk_team_layer_strength, def_team_layer_strength, 0, 0):
                            if battle_layer[1] == Position.GK:
                                #print(atk_team_layer_strength, def_team_layer_strength)
                                atk_team.goals += 1
                            continue
                        else: break

            hg = self.home_team.goals
            ag = self.away_team.goals

            results.update({(hg,ag): results.get((hg,ag),0)+1})
            x=0
            if hg<ag: x=2
            elif hg==ag: x=1
            home_draw_away[x] += 1
            scored_goals[0] += hg
            scored_goals[1] += ag

        print("Home: {}    Draw: {}    Away: {}".format(home_draw_away[0], home_draw_away[1], home_draw_away[2]))
        print("Home: {}%    Draw: {}%    Away: {}%".format(int(round(100*home_draw_away[0]/n_matches)),
                                                              int(round(100*home_draw_away[1]/n_matches)),
                                                              int(round(100*home_draw_away[2]/n_matches))))
        print("Home Scored: {} \nAway Scored: {}".format(scored_goals[0], scored_goals[1]))

        mlrs = [(key, value) for key, value in results.items()]
        mlrs.sort(key=lambda item: item[1], reverse=True)

        print("Most likely result ?")

        for mlr in mlrs:
            print("{}-{} with {}%".format(mlr[0][0], mlr[0][1], int(round(100*mlr[1]/n_matches))))

def test_real_match():
    project_path = "/home/gillabo/Desktop/soccersim"

    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("no-sandbox")
    #chrome_options.add_argument("headless")
    chrome_options.add_argument("start-maximized")
    chrome_options.add_argument("window-size=1900,1080")
    driver = webdriver.Chrome(executable_path=project_path + "/res/chromedriver", chrome_options=chrome_options)

    fifa_index_link = "https://www.fifaindex.com/"
    driver.get(fifa_index_link)
    fifa_index_handler = driver.current_window_handle

    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])

    rez_match_link = input()
    driver.get(rez_match_link)
    rez_match_handler = driver.current_window_handle

    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, "li-match-lineups"))).click()
    home_player_elements = WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "summary-vertical.fl")))[:11]
    away_player_elements = WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "summary-vertical.fr")))[:11]

    player_elements = home_player_elements + away_player_elements
    i = 0
    animation = ["[#.........]", "[##........]", "[###.......]", "[####......]", "[#####.....]", "[######....]",
                 "[#######...]", "[########..]", "[#########.]", "[##########]"]

    for player_element in player_elements:
        clear()
        print("Scraping:")
        print("\r" + animation[int(round(i/21 * len(animation)))])

        driver.execute_script(player_element.find_element_by_tag_name("a").get_attribute("onclick"))
        driver.switch_to.window(driver.window_handles[-1])
        name = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "teamHeader__name"))).text.rstrip()
        #name = driver.find_element_by_class_name("teamHeader__name").text.rstrip()
        pos = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "teamHeader__info--player-type-name"))).text.split(" ")[0]
        #pos = driver.find_element_by_class_name("teamHeader__info--player-type-name").text.split(" ")[0]
        driver.close()

        driver.switch_to.window(fifa_index_handler)
        input_name = driver.find_element_by_id("id_name")
        input_name.clear()
        input_name.send_keys(name)
        input_name.send_keys(Keys.ENTER)

        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.CLASS_NAME, "link-player"))).click()

        x = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, '/html/body/main/div/div[2]/div[2]/div[2]/div[2]/div/h5/span/span[1]')))
        ovr = int(x.text)
        pot = int(driver.find_element_by_xpath('/html/body/main/div/div[2]/div[2]/div[2]/div[2]/div/h5/span/span[2]').text)
        age = int(driver.find_element_by_xpath('/html/body/main/div/div[2]/div[2]/div[2]/div[2]/div/div/p[5]/span').text)
        work_rate = driver.find_element_by_xpath('/html/body/main/div/div[2]/div[2]/div[2]/div[2]/div/div/p[7]/span').text.split(" ")
        awr = work_rate[0]
        dwr = work_rate[2]
        driver.back()
        driver.switch_to.window(rez_match_handler)
        print(name, age, ovr, pot, pos, awr, dwr)
        if i<11: home_players.append(Player(name, age, ovr, pot, pos, awr, dwr))
        else: away_players.append(Player(name, age, ovr, pot, pos, awr, dwr))
        i+=1
    driver.close()

def test_match():
    for i in range(11):
        if i==0: home_players.append(Player("Test", 24, 87, 89, "Golman", "Medium", "Medium"))
        elif i<5: home_players.append(Player("Test", 24, 87, 89, "Branič", "Medium", "Medium"))
        elif i < 8: home_players.append(Player("Test", 24, 87, 89, "Veznjak", "Medium", "Medium"))
        else: home_players.append(Player("Test", 24, 87, 89, "Napadač", "Medium", "Medium"))

    for i in range(11):
        if i==0: away_players.append(Player("Test", 24, 87, 89, "Golman", "Medium", "Medium"))
        elif i<5: away_players.append(Player("Test", 24, 87, 89, "Branič", "Medium", "Medium"))
        elif i < 8: away_players.append(Player("Test", 24, 80, 86, "Veznjak", "Medium", "Medium"))
        else: away_players.append(Player("Test", 24, 75, 75, "Napadač", "Medium", "Medium"))

home_players = []
away_players = []
test_real_match()
match = Match(Team(home_players), Team(away_players))
match.simulate(3000, 100)