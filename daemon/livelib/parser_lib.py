import re

def re_compiler(preg):
    return re.compile(preg, re.IGNORECASE)

server_cvar_value = re_compiler(r'"([A-Za-z\_]+)" = "(.*?)"$')

log_file_started = re_compiler(r'^L ([0-9\/]+) - ([0-9\:]+) Log file started \x28file "(.*?)"\x29.*$')
log_timestamp = re_compiler(r'^L ([0-9\/]+) - ([0-9\:]+):.*$')
#L 10/01/2012 - 21:38:17: "LIVELOG_LOGGING_START"
logging_start = re_compiler(r'^L ([0-9\/]+) - ([0-9\:]+): "LIVELOG_LOGGING_START"$')

game_restart = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "LIVELOG_GAME_RESTART"$')
game_end = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "LIVELOG_GAME_END"$')

# L 10/01/2012 - 21:43:10: "[v3] Roight<53><STEAM_0:0:8283620><Red>" triggered "damage" (damage "208")
damage_dealt = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "damage" \x28damage "(\d+)"\x29$')
damage_taken = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "damage_taken" \x28damage "(\d+)"\x29$')

healing_done = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "healed" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>" \x28healing "(\d+)"\x29$')

#"D5+ :happymeat:<24><STEAM_0:1:44157999><Blue>" triggered "overhealed" against "GBH | Mongo<20><STEAM_0:0:14610972><Blue>" (overhealing "28")
overhealing_done = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "overhealed" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>" \x28overhealing "(\d+)"\x29$')

item_pickup = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" picked up item "(.*?)"$')
#L 04/12/2014 - 04:12:16: "playboater<3><STEAM_0:1:27952643><Blue>" picked up item "medkit_medium" (healing "88")
item_healing = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" picked up item "(.*?)" \x28healing "(\d+)"\x29$')

medic_death = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "medic_death" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>" \x28healing "(.*?)"\x29 \x28ubercharge "(.*?)"\x29$')
uber_used = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "chargedeployed"(\s?\x28medigun "(.*?)"\x29)?$')
#"Slamm<13><STEAM_0:0:5390368><Blue>" triggered "chargedeployed" (medigun "medigun")
#uber_used_ex = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "chargedeployed" \x28medigun "(.*?)"\x29$')

chat_message = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue|Spectator|Console)>" (say|say_team) "(.+)"$')

point_capture = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: Team "(Blue|Red)" triggered "pointcaptured" \x28cp "(\d+)"\x29 \x28cpname "(.*?)"\x29 \x28numcappers "(\d+)".*$')
capture_blocked = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "captureblocked" \x28cp "(\d+)"\x29 \x28cpname "#?(.*?)"\x29 \x28position "(.*?)"\x29$')

team_score = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: Team "(Blue|Red)" current score "(\d+)" with "(\d+)" players$')
final_team_score = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: Team "(Blue|Red)" final score "(\d+)" with "(\d+)" players$')
game_over = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Game_Over" reason "(.*?)"$')

rcon_command = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: rcon from "(.*?)": command "(.*?)"$')

building_destroyed = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "killedobject" \x28object "(.*?)"\x29 \x28weapon "(.*?)"\x29 \x28objectowner "(.*?)<(\d+)><(.*?)><(Blue|Red)>"\x29 \x28attacker_position "(.*?)"\x29$')

#"Gucci_Cooki^<75><STEAM_0:0:43662794><Blue>" triggered "killedobject" (object "OBJ_SENTRYGUN") (objectowner "faith<63><STEAM_0:0:52150090><Red>") (assist "1") (assister_position "596 275 505") (attacker_position "881 473 544")
building_destroyed_assist = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "killedobject" \x28object "(.*?)"\x29 \x28objectowner "(.*?)<(\d+)><(.*?)><(Blue|Red)>"\x29 \x28assist "\d"\x29 \x28assister_position "(.*?)"\x29 \x28attacker_position "(.*?)"\x29$')

#"|S| ynth<13><STEAM_0:1:2869609><Red>" triggered "builtobject" (object "OBJ_TELEPORTER") (position "-4165 1727 -511")
building_created = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "builtobject" \x28object "(.*?)"\x29 \x28position "(.*?)"\x29$')

#"Cinderella:wu<5><STEAM_0:1:18947653><Blue>" triggered "damage" against "jmh<19><STEAM_0:1:101867><Red>" (damage "56")
player_damage = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "damage" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>" \x28damage "(\d+)"\x29$')
player_damage_weapon = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "damage" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>" \x28damage "(\d+)"\x29 \x28weapon "(\d+)"\x29$')

# L 10/01/2012 - 21:43:10: "[v3] Roight<53><STEAM_0:0:8283620><Red>" triggered "domination" against "Liquid'zato<46><STEAM_0:0:42607036><Blue>"
# L 10/01/2012 - 22:04:57: "Liquid'Iyvn<40><STEAM_0:1:41931908><Blue>" triggered "domination" against "[v3] Kaki<51><STEAM_0:1:35387674><Red>" (assist "1")
player_dominated = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "domination" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>".*$')

# L 10/01/2012 - 21:51:37: "Liquid'zato<46><STEAM_0:0:42607036><Blue>" triggered "revenge" against "[v3] Roight<53><STEAM_0:0:8283620><Red>"
# L 10/01/2012 - 22:08:58: "Liquid'Time<41><STEAM_0:1:19238234><Blue>" triggered "revenge" against "[v3] Chrome<48><STEAM_0:1:41365809><Red>" (assist "1")
player_revenge = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "revenge" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>".*$')

# "Hypnos<20><STEAM_0:0:24915059><Red>" committed suicide with "world" (customkill "train") (attacker_position "568 397 -511")
player_suicide_custom = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" committed suicide with "(.*?)" \x28customkill "(.*?)"\x29 \x28attacker_position "(.*?)"\x29$')

# 11/13/2012 - 23:03:29: "crixus of gaul<3><STEAM_0:1:10325827><Blue>" committed suicide with "tf_projectile_rocket" (attacker_position "-1233 5907 -385")
player_suicide = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" committed suicide with "(.*?)" \x28attacker_position "(.*?)"\x29$')

player_kill = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" killed "(.*?)<(\d+)><(.*?)><(Red|Blue)>" with "(.*?)" \x28attacker_position "(.*?)"\x29 \x28victim_position "(.*?)"\x29$')
player_kill_special = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" killed "(.*?)<(\d+)><(.*?)><(Red|Blue)>" with "(.*?)" \x28customkill "(.*?)"\x29 \x28attacker_position "(.*?)"\x29 \x28victim_position "(.*?)"\x29$')
player_assist = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "kill assist" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>" \x28assister_position "(.*?)"\x29 \x28attacker_position "(.*?)"\x29 \x28victim_position "(.*?)"\x29$')

#"ph.tw|n<19><STEAM_0:0:39342123><Red>" triggered "player_extinguished" against "Mad<11><STEAM_0:0:41824190><Red>" with "tf_weapon_flamethrower" (attacker_position "-1504 -2949 -408") (victim_position "-1542 -2970 -408")
player_extinguish = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "player_extinguished" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>" with "(.*?)" \x28attacker_position "(.*?)"\x29 \x28victim_position "(.*?)"\x29$')

#"Colonel Turtle<41><STEAM_0:0:50524471><Blue>" triggered "milk_attack" against "Bioxide.nK,nC<37><STEAM_0:0:52924883><Red>" with "tf_weapon_jar" (attacker_position "456 -1028 299") (victim_position "733 -314 431")
player_jar_attack = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "(.*?)" against "(.*?)<(\d+)><(.*?)><(Red|Blue)>" with "tf_weapon_jar" \x28attacker_position "(.*?)"\x29 \x28victim_position "(.*?)"\x29$')

# L 04/12/2014 - 04:12:26: "playboater<3><STEAM_0:1:27952643><Blue>" triggered "shot_fired" (weapon "tf_projectile_pipe")
player_shot_fired = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" triggered "shot_fired" \x28weapon "(.*?)"\x29$')

player_disconnect = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(.*?)>" disconnected \x28reason "(.*?)"\x29$')
player_connect = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><>" connected, address "(.*?):(.*?)"$')
player_validated = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><>" STEAM USERID validated$')

#"zeej<51><STEAM_0:0:41289089><>" entered the game
player_entered_game = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><>" entered the game$')

player_class_change = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" changed role to "(.*?)"$')
#"[v3] Kaki<51><STEAM_0:1:35387674><Red>" spawned as "soldier"
player_spawn = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue)>" spawned as "(.*?)"$')

#"b1z<19><STEAM_0:0:18186373><Red>" joined team "Blue"
player_team_join = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue|Spectator|Unassigned)>" joined team "(Red|Blue|Spectator)"$')

#"hobbes<64><STEAM_0:0:19415161><Red>" changed name to "Smauglet"
player_name_change = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: "(.*?)<(\d+)><(.*?)><(Red|Blue|Spectator|Unassigned)>" changed name to "(.*?)"$')

round_win = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Win" \x28winner "(Blue|Red)"\x29$')
round_overtime = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Overtime"$')
round_length = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Length" \x28seconds "(\d+)\.(\d+)"\x29$')
round_start = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Start"$')
round_setup_start = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Setup_Begin"$')
round_setup_end = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Round_Setup_End"$')

#L 04/11/2014 - 18:45:48: World triggered "Mini_Round_Win" (winner "Blue") (round "round_a")
mini_round_win = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Mini_Round_Win" \x28winner "(Blue|Red)"\x29 \x28round "(.*?)"\x29$')
mini_round_length = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Mini_Round_Length" \x28seconds "(\d+.\d+)"\x29$')
mini_round_selected = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Mini_Round_Selected" \x28round "(.*?)"\x29$')
mini_round_start = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: World triggered "Mini_Round_Start"$')

#L 03/07/2013 - 18:00:26: Loading map "cp_granary"
#L 03/07/2013 - 18:00:27: Started map "cp_granary" (CRC "4f34345d09eff7fc96af9a421e81a4b8")
#L 03/07/2013 - 18:00:27: -------- Mapchange to cp_granary --------
map_change = re_compiler(r'^L [0-9\/]+ - [0-9\:]+: Started map "(.*?)" \x28CRC "(.*?)"\x29$')


class ParserException(Exception):
    """
    Raised for known exceptions like an invalid steamid
    """
    pass


"""
The player data object
"""
class PlayerData(object):
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
        # Mark a class as being played and set the current class to the
        # new class
        if pclass in self._player_class:
            self._player_class[pclass] = True

            self._current_player_class = pclass

    def class_played(self, pclass):
        # If the class is valid, return whether it has been played. If invalid,
        # return false
        if pclass in self._player_class:
            return self._player_class[pclass]
        else:
            return False

    def class_string(self):
        # Join played classes together in a string. No longer used
        return ','.join(self.class_list())

    def class_list(self):
        return [ x for x in self._player_class if self._player_class[x] ]

    def current_class(self):
        """
        Return the current class. If the class has not been set (i.e is None),
        we return "UNKNOWN". This constant is used in the websocket dbmanager
        and by the log page JavaScript. Therefore, if it is changed, those will
        also need to be updated.
        """

        if self._current_player_class is not None:
            return self._current_player_class
        else:
            return "UNKNOWN"

    def set_class(self, pclass):
        self._current_player_class = pclass

        if not self.class_played(pclass):
            # reset the team, so the next team insert will update this player's
            # teams for all classes
            self.set_team(None) 

    def set_name(self, name):
        self._player_name = name

    def is_name_same(self, name):
        return name == self._player_name

    def current_name(self):
        return self._player_name

    def set_team(self, team):
        self._player_team = team

    def is_team_same(self, team):
        # Check if the given team is equal to the current team
        return team == self._player_team

    def current_team(self):
        """
        Return the current team. If the team has not been set (i.e is None),
        we return "None". This constant is used in the websocket dbmanager
        and by the log page JavaScript. Therefore, if it is changed, those will
        also need to be updated.
        """

        if self._player_team is None:
            return "None"
        else:
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
    # takes a steamid in the format STEAM_x:x:xxxxx or [U:1:xxxx] and converts
    # it to a 64bit community id

    if steam_id == "BOT" or steam_id == "0":
        return steam_id

    cm_modifier = 76561197960265728
    account_id = 0

    # support oldage STEAM_0:A:B user SteamIDs (TF2 now uses [U:1:2*B+A])
    if "STEAM_" in steam_id:
        auth_server = 0
        auth_id = 0
        
        steam_id_tok = steam_id.split(':')

        if len(steam_id_tok) == 3:
            auth_server = int(steam_id_tok[1])
            auth_id = int(steam_id_tok[2])
            
            account_id = auth_id * 2 #multiply auth id by 2
            account_id += auth_server #add the auth server. even ids are on server 0, odds on server 1

    elif "[U:1:" in steam_id:
        # steamid is [U:1:####]. All we need to do is get the #### out and add
        # the 64bit 76561197960265728
        account_id = re.sub(r'(\[U:1:)|(\])', "", steam_id)
        if bool(account_id):
            account_id = int(account_id)
    else:
        raise ParserException("Invalid SteamID: '%s'" % steam_id)    

    if not bool(account_id):
        raise ParserException("Invalid SteamID: '%s' gives AccountID '%d'" % (steam_id, account_id))

    # Have non-zero account id. Add the community ID modifier
    community_id = account_id + cm_modifier #add arbitrary number chosen by valve

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

