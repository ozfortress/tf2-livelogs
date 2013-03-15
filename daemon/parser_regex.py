#preg = re.compile(expression, re.IGNORECASE | re.MULTILINE)
import re

def re_compiler(preg):
    return re.compile(preg, re.IGNORECASE | re.MULTILINE)

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
player_disconnect = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue|Spectator)>" disconnected \x28reason "(.*)"\x29')
player_connect = re_compiler(r'"(.*)<(\d+)><(.*)><>" connected, address "(.*):(.*)"')
player_validated = re_compiler(r'"(.*)<(\d+)><(.*)><>" STEAM USERID validated')
player_class_change = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" changed role to "(.*)"')
#"b1z<19><STEAM_0:0:18186373><Red>" joined team "Blue"
player_team_join = re_compiler(r'"(.*)<(\d+)><(.*)><(Red|Blue|Spectator)>" joined team "(.*)"')


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