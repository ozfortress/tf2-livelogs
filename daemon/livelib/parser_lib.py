#preg = re.compile(expression, re.IGNORECASE | re.MULTILINE)
import re

def re_compiler(preg):
    return re.compile(preg, re.IGNORECASE | re.MULTILINE)

server_cvar_value = re_compiler(r'"([A-Za-z\_]+)" = "(.*)"')

log_file_started = re_compiler(r'L (\S+) - (\S+) Log file started \x28file "(.*)"\x29')
log_timestamp = re_compiler(r'L (\S+) - (\S+):')

game_restart = re_compiler(r'"LIVELOG_GAME_RESTART"')

damage_dealt = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "damage" \x28damage "(\d+)"\x29')
damage_taken = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "damage_taken" \x28damage "(\d+)"\x29')

healing_done = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "healed" against "(.*)<(\d+)><(.*)><(Red|Blue)>" \x28healing "(\d+)"\x29')
item_pickup = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" picked up item "(.*)"')

medic_death = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "medic_death" against "(.*)<(\d+)><(.*)><(Red|Blue)>" \x28healing "(.*)"\x29 \x28ubercharge "(.*)"\x29')
uber_used = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "chargedeployed"')

chat_message = re_compiler(r'"(.+)<(\d+)><(.+)><(Red|Blue|Spectator|Console)>" (say|say_team) "(.+)"')

point_capture = re_compiler(r'Team "(Blue|Red)" triggered "pointcaptured" \x28cp "(\d+)"\x29 \x28cpname "(.*)"\x29 \x28numcappers "(\d+)"')
capture_blocked = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "captureblocked" \x28cp "(\d+)"\x29 \x28cpname "#?(.*)"\x29 \x28position "(.*)"\x29')

team_score = re_compiler(r'Team "(Blue|Red)" current score "(\d+)" with "(\d+)" players')
final_team_score = re_compiler(r'Team "(Blue|Red)" final score "(\d+)" with "(\d+)" players')
game_over = re_compiler(r'World triggered "Game_Over" reason "(.*)"')

rcon_command = re_compiler(r'rcon from "(.*)": command "(.*)"')

building_destroyed = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "killedobject" \x28object "(.*)"\x29 \x28weapon "(.*)"\x29 \x28objectowner "(.*)<(\d+)><(.*)><(Blue|Red)>"\x29 \x28attacker_position "(.*)"\x29')
#"Gucci_Cooki^<75><STEAM_0:0:43662794><Blue>" triggered "killedobject" (object "OBJ_SENTRYGUN") (objectowner "faith<63><STEAM_0:0:52150090><Red>") (assist "1") (assister_position "596 275 505") (attacker_position "881 473 544")
building_destroyed_assist = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "killedobject" \x28object "(.*)"\x29 \x28objectowner "(.*)<(\d+)><(.*)><(Blue|Red)>"\x29 \x28assist "\d"\x29 \x28assister_position "(.*)"\x29 \x28attacker_position "(.*)"\x29')
#"|S| ynth<13><STEAM_0:1:2869609><Red>" triggered "builtobject" (object "OBJ_TELEPORTER") (position "-4165 1727 -511")
building_created = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "builtobject" \x28object "(.*)"\x29 \x28position "(.*)"\x29')

#"Cinderella:wu<5><STEAM_0:1:18947653><Blue>" triggered "damage" against "jmh<19><STEAM_0:1:101867><Red>" (damage "56")
player_damage = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "damage" against "(.*)<(\d+)><(.*)><(Red|Blue)>" \x28damage "(\d+)"\x29')
player_dominated = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "domination" against "(.*)<(\d+)><(.*)><(Red|Blue)>"')
player_revenge = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "revenge" against "(.*)<(\d+)><(.*)><(Red|Blue)>"')
player_death_custom = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" committed suicide with "(.*)" \x28customkill "(.*)"\x29')
player_death = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" committed suicide with "(.*)"')
player_kill = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" killed "(.*)<(\d+)><(.*)><(Red|Blue)>" with "(.*)" \x28attacker_position "(.*)"\x29 \x28victim_position "(.*)"\x29')
player_kill_special = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" killed "(.*)<(\d+)><(.*)><(Red|Blue)>" with "(.*)" \x28customkill "(.*)"\x29 \x28attacker_position "(.*)"\x29 \x28victim_position "(.*)"\x29')
player_assist = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "kill assist" against "(.*)<(\d+)><(.*)><(Red|Blue)>" \x28assister_position "(.*)"\x29 \x28attacker_position "(.*)"\x29 \x28victim_position "(.*)"\x29')
#"ph.tw|n<19><STEAM_0:0:39342123><Red>" triggered "player_extinguished" against "Mad<11><STEAM_0:0:41824190><Red>" with "tf_weapon_flamethrower" (attacker_position "-1504 -2949 -408") (victim_position "-1542 -2970 -408")
player_extinguish = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "player_extinguished" against "(.*)<(\d+)><(.*)><(Red|Blue)>" with "(.*)" \x28attacker_position "(.*)"\x29 \x28victim_position "(.*)"\x29')
player_disconnect = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue|Spectator)>" disconnected \x28reason "(.*)"\x29')
player_connect = re_compiler(r'"(.*)<(\d+)><(.*)><>" connected, address "(.*):(.*)"')
player_validated = re_compiler(r'"(.*)<(\d+)><(.*)><>" STEAM USERID validated')
#"zeej<51><STEAM_0:0:41289089><>" entered the game
player_entered_game = re_compiler(r'"(.*)<(\d+)><(.*)><>" entered the game')
player_class_change = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" changed role to "(.*)"')
#"b1z<19><STEAM_0:0:18186373><Red>" joined team "Blue"
player_team_join = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue|Spectator|Unassigned)>" joined team "(Red|Blue|Spectator)"')
#"hobbes<64><STEAM_0:0:19415161><Red>" changed name to "Smauglet"
player_name_change = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue|Spectator|Unassigned)>" changed name to "(.*)"')

round_win = re_compiler(r'World triggered "Round_Win" \x28winner "(Blue|Red)"\x29')
round_overtime = re_compiler(r'World triggered "Round_Overtime"')
round_length = re_compiler(r'World triggered "Round_length" \x28seconds "(\d+)\.(\d+)"\x29')
round_start = re_compiler(r'World triggered "Round_Start"')
round_setup_end = re_compiler(r'World triggered "Round_Setup_End"')

mini_round_win = re_compiler(r'World triggered "Mini_Round_Win" \x28winner "(Blue|Red)"\x29 \x28round "round_(\d+)"\x29')
mini_round_length = re_compiler(r'World triggered "Mini_Round_Length" \x28seconds "(\d+.\d+)"\x29')

#L 03/07/2013 - 18:00:26: Loading map "cp_granary"
#L 03/07/2013 - 18:00:27: Started map "cp_granary" (CRC "4f34345d09eff7fc96af9a421e81a4b8")
#L 03/07/2013 - 18:00:27: -------- Mapchange to cp_granary --------
map_change = re_compiler(r'Started map "(.*)" \x28CRC "(.*)"\x29')

"""
The player data object
"""
class player_data(object):
    #class to hold all player information that is set throughout parsing the log
    def __init__(self, pclass, name, team):
        self.details_inserted = False

        self._player_class = {
            "scout": False,
            "soldier": False,
            "pyro": False,
            "demoman": False,
            "heavyweapons": False,
            "medic": False,
            "sniper": False,
            "engineer": False,
            "spy": False
        } #all classes default to false
        self._current_player_class = None

        self._player_name = None
        self._player_team = None

        if pclass:
            self._player_class[pclass] = True #add the class to the player's data
            self.set_class(pclass)

        if name:
            self._player_name = name

        if team:
            self._player_team = team

    def add_class(self, pclass):
        if pclass in self._player_class:
            self._player_class[pclass] = True

            self._current_player_class = pclass

    def class_played(self, pclass):
        if pclass in self._player_class:
            return self._player_class[pclass]
        else:
            return False

    def class_string(self):
        class_list = []

        for pclass in self._player_class:
            if self._player_class[pclass]:
                class_list.append(pclass)

        return ','.join(class_list)

    def current_class(self):
        if self._current_player_class:
            return self._current_player_class
        else:
            return "UNKNOWN"

    def set_class(self, pclass):
        self._current_player_class = pclass

        if not self.class_played(pclass):
            self.set_team(None) #reset the team, so the next team insert will update this player's teams for all classes

        #print "%s: current class set to %s" % (self._player_name, pclass)

    def set_name(self, name):
        self._player_name = name

    def is_name_same(self, name):
        return name == self._player_name

    def current_name(self):
        return self._player_name

    def set_team(self, team):
        self._player_team = team

    def is_team_same(self, team):
        return team == self._player_team

    def current_team(self):
        return self._player_team


from HTMLParser import HTMLParser

#this class is used to remove all HTML tags from player strings
class HTMLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = [] #fed is what is fed to the class by the function

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)

def stripHTMLTags(string):
    stripper = HTMLStripper()
    stripper.feed(string)


    return stripper.get_data() #get the text out

"""
definitions of functions used by the parser
"""
item_dict = {
            'ammopack_small': 'ap_small',
            'ammopack_medium': 'ap_medium', 
            'tf_ammo_pack': 'ap_large', 
            'medkit_small': 'mk_small', 
            'medkit_medium': 'mk_medium', 
            'medkit_large': 'mk_large'
        }

def selectItemName(item_name):
    if item_name in item_dict:
        return item_dict[item_name]
    else:
        return None

def get_cid(steam_id):
    #takes a steamid in the format STEAM_x:x:xxxxx and converts it to a 64bit community id

    auth_server = 0;
    auth_id = 0;
    
    steam_id_tok = steam_id.split(':')

    if len(steam_id_tok) == 3:
        auth_server = int(steam_id_tok[1])
        auth_id = int(steam_id_tok[2])
        
        community_id = auth_id * 2 #multiply auth id by 2
        community_id += 76561197960265728 #add arbitrary number chosen by valve
        community_id += auth_server #add the auth server. even ids are on server 0, odds on server 1

    else:
        community_id = 0

    return community_id

def escapePlayerString(unescaped_string):

    def remove_non_ascii(string):
        return "".join(i for i in string if ord(i) < 128)


    escaped_string = unescaped_string.decode('utf-8', 'ignore') #decode strings into unicode where applicable
    escaped_string = escaped_string.replace("'", "''").replace("\\", "\\\\") #escape slashes and apostrophes
    #escaped_string = remove_non_ascii(escaped_string)
    escaped_string = stripHTMLTags(escaped_string) #strip any html tags

    if len(escaped_string) == 0:
        return "LL_INVALID_STRING"; #if the string is empty, return invalid string

    return escaped_string

