try:
    import psycopg2
except ImportError:
    print """You are missing psycopg2.
    Install using `pip install psycopg2` or visit http://initd.org/psycopg/
    """
    quit()

import time
import struct
import re
import os
import threading

import logging

from pprint import pprint
from livelib import parser_lib, queryqueue

# classes typically joined as to swap between forward/back spawns, don't add 
# these classes unless player gets a kill
spawn_swap_classes = ["spy", "sniper", "pyro", "engineer"] 

# helper for performing regex checks
def regex(compiled_regex, string):
    #preg = re.compile(expression, re.IGNORECASE | re.MULTILINE)
    
    match = compiled_regex.match(string)

    return match

# helper for getting regex elements
def regml(retuple, index): #get index of re group tuple
    return retuple.group(index)


class parserClass(object):
    def __init__(self, data, endfunc = None, log_uploaded = False):
        self.HAD_ERROR = False
        self.LOG_FILE_HANDLE = None
        self._log_file_writes = 0
        self.db = data.db

        self._weapon_data = data.weapon_data
        self._master_query_queue = data.query_queue

        unique_ident = data.unique_parser_ident

        self.logger = logging.getLogger(unique_ident)
        self.logger.setLevel(logging.DEBUG)

        self.__log_file_lock = threading.Lock()
        self.__end_log_lock = threading.Lock()

        self.closeListenerCallback = endfunc
        
        self.UNIQUE_IDENT = unique_ident
        self.GAME_OVER = False
        self.ROUND_PAUSE = False
        self.LOG_PARSING_ENDED = False

        #if no map is specified (auto detect), set map to 0
        if (data.log_map == None):
            self.current_map = 0
        else:
            self.current_map = data.log_map

        if (data.log_webtv_port == None):
            data.log_webtv_port = 0

        # insert the log into the index table        
        self.INDEX_TABLE = "livelogs_log_index"

        try:
            conn = self.db.getconn()
        except:
            self.logger.exception("Exception getting database connection")

            self.HAD_ERROR = True

            self.__cleanup()
            return

        try:
            dbCursor = conn.cursor()

            if (data.client_address != None):
                # make up a name if the log name is empty
                if not data.log_name:
                    data.log_name = "log-%s" % time.strftime("%Y-%m-%d-%H-%M") #log-year-month-day-hour-minute
                
                # if the log is uploaded, 0 details
                if log_uploaded:
                    address = "0.0.0.0"
                    port = "000000"

                else:
                    address = data.client_address[0]
                    port = str(data.client_address[1])

                # perform an insert query with a return, so that the numeric
                # id of the log is returned. we need this id to send to the
                # game server so clients can get the log url
                dbCursor.execute("""INSERT INTO livelogs_log_index (server_ip, server_port, api_key, log_ident, 
                                                                    map, log_name, live, webtv_port, tstamp)
                                    VALUES (%s, %s, %s, %s, %s, %s, 'true', %s, %s) 
                                    RETURNING numeric_id""", (
                                        address, port, data.api_key, self.UNIQUE_IDENT, self.current_map, 
                                        data.log_name, data.log_webtv_port, time.strftime("%Y-%m-%d %H:%M:%S"),
                                    )
                            )

                return_data = dbCursor.fetchone()

                if return_data:
                    self._numeric_id = return_data[0]
                else:
                    self._numeric_id = 0

            conn.commit()

        except:
            self.logger.exception("Exception during table init")

            self.HAD_ERROR = True

            self.__cleanup(conn, dbCursor)

            return

        self.__close_db_components(conn, dbCursor)

        self.EVENT_TABLE = "livelogs_game_events"
        self.KILL_EVENT_TABLE = "livelogs_kill_events"
        self.MEDIC_EVENT_TABLE = "livelogs_medic_events"
        self.STAT_TABLE = "livelogs_player_stats"
        self.CHAT_TABLE = "livelogs_game_chat"
        self.PLAYER_TABLE = "livelogs_player_details"
            
        self._players = {} #a dict of player data objects wrt steamid
        
        # store current epoch time as the start time, which is used to determine
        # the duration of the log when ending
        self.__start_time = time.time()

        self._have_final_scores = {
            "blue": False,
            "red": False
        }

        self._first_round_started = False
        self._last_event_times = None
        self.paused = False

        # If we're using supstats we prevent logging of some specific data
        # in other events, such as headshots in custom kills.
        self._using_supstats = False

        self.create_log_file(unique_ident)

        self.logger.info("Parser initialised")

    def create_log_file(self, unique_ident):
        import ConfigParser
        cfg_parser = ConfigParser.SafeConfigParser()

        have_log_dir = False
        if cfg_parser.read(r'll-config.ini'):
            try:
                log_dir = cfg_parser.get('log-listener', 'log_directory')
                have_log_dir = True
                
            except:
                self.logger.exception("Unable to read log directory from config file")
        else:
            self.logger.error("Error reading config file")
        
        if have_log_dir:
            try:
                if not os.path.exists(log_dir):
                    #need to make the directory
                    os.makedirs(log_dir, 0755)
                    
                log_file_name = "%s.log" % unique_ident
                log_file = os.path.normpath(os.path.join(log_dir, log_file_name))
                
                self.LOG_FILE_HANDLE = open(log_file, 'w')
                
            except OSError:
                self.logger.exception("Error opening new log file for writing, or creating log directory")

    # the parsing method. kinda big, but not really feasible to separate it i think
    def parse(self, logdata):
        if (not logdata) or (not self.db) or self.GAME_OVER or self.HAD_ERROR or self.LOG_PARSING_ENDED:
            return

        try:
            event_time = None

            if not "rcon" in logdata:
                self.write_to_log(logdata + "\n")

            #log file start
            #RL 10/07/2012 - 01:13:34: Log file started (file "logs_pug/L1007104.log") (game "/games/tf2_pug/orangebox/tf") (version "5072")
            res = regex(parser_lib.log_file_started, logdata)
            if res:
                #print "Log file started"
                #pprint(res.groups())
                #do shit with log file name?
                
                return

            #log time
            res = regex(parser_lib.log_timestamp, logdata)
            if res:
                #print "Time of current log"
                #pprint(res.groups())
                
                event_time = "%s %s" % (regml(res, 1), regml(res, 2))

                # a tuple of the date, time event combination
                self._last_event_times = (regml(res, 1), regml(res, 2))
            
            if not event_time:
                return

            # log start
            # if we've already gotten a round_start message before this, ignore this message
            # otherwise we will have an extra round_start
            if not self._first_round_started:
                res = regex(parser_lib.logging_start, logdata)
                if res:
                    # the game has just started, we have NOT gotten a Round_start message,
                    # so we will add one to the log file. this message is necessary because
                    # otherwise the first Round_Start is cut off, and 3rd party parsers will
                    # not be able to parse the first round properly using this log file
                    self.write_to_log("L %s - %s: World triggered \"Round_Start\"\n" % (regml(res, 1), regml(res, 2),))

                    return

            #log restart, sent when a mp_restartgame is issued (need a new log file, so we end this one)
            res = regex(parser_lib.game_restart, logdata)
            if res:
                #end the log

                self.logger.info("Game restart message received. Closing this log file")

                self.GAME_OVER = True
                self.endLogParsing(True)

                return

            res = regex(parser_lib.game_end, logdata)
            if res:
                # game is over, end the log
                self.logger.info("Game end message received. Closing this log file")

                self.GAME_OVER = True
                self.endLogParsing(True)

                return

            #don't want to record stats that happen after round_win (bonustime kills and shit)
            if not self.ROUND_PAUSE:
            #begin round_pause blocking

                # Shots fired/hit will be the most common. Check them first
                res = regex(parser_lib.player_shot_fired, logdata)
                if res:
                    return

                res = regex(parser_lib.player_shot_hit, logdata)
                if res:
                    return

                # Old damage log message
                res = regex(parser_lib.player_damage, logdata)
                if res:
                    return

                # damage taken and dealt. note that realdamage, healing, crit, airshot and headshot are not
                # always present...
                #[[attacker]] triggered "damage" against [[victim]] (damage "0") (realdamage "0")? (weapon "shotgun_soldier") (healing "15")? (crit "crit|mini")? (airshot "1")? (headshot "1")?
                res = regex(parser_lib.player_damage_weapon, logdata)
                if res:
                    self._using_supstats = True

                    a_sid = regml(res, 3)
                    a_name = parser_lib.escapePlayerString(regml(res, 1))

                    v_sid = regml(res, 7)
                    v_name = parser_lib.escapePlayerString(regml(res, 5))

                    dmg = int(regml(res, 9))

                    realdamage = regml(res, "rd")
                    healing = regml(res, "heal")
                    crit = regml(res, "crit")
                    airshot = regml(res, "as")
                    headshot = regml(res, "hs")

                    self.insert_player_team(a_sid, regml(res, 4))

                    if realdamage is not None:
                        dmg = int(realdamage)

                    if healing is not None:
                        pass

                    if airshot is not None:
                        self.stat_upsert(self.STAT_TABLE, "airshots", a_sid, a_name, int(airshot))

                    if headshot is not None:
                        self.stat_upsert(self.STAT_TABLE, "headshots", a_sid, a_name, 1)
                    
                    if a_sid != v_sid: #players can deal self damage. if so, don't record damage_dealt for this
                        self.stat_upsert(self.STAT_TABLE, "damage_dealt", a_sid, a_name, dmg)
                        self.insert_player_team(v_sid, regml(res, 8))

                    self.stat_upsert(self.STAT_TABLE, "damage_taken", v_sid, v_name, dmg)

                    return

                #overhealing done
                #"D5+ :happymeat:<24><STEAM_0:1:44157999><Blue>" triggered "overhealed" against "GBH | Mongo<20><STEAM_0:0:14610972><Blue>" (overhealing "28")
                res = regex(parser_lib.overhealing_done, logdata)
                if res:
                    medic_sid = regml(res, 3)
                    medic_name = parser_lib.escapePlayerString(regml(res, 1))
                    medic_overhealing = int(regml(res, 9))

                    healt_name = parser_lib.escapePlayerString(regml(res, 5))
                    healt_sid = regml(res, 7)

                    self.insert_player_team(medic_sid, regml(res, 4))
                    self.insert_player_team(healt_sid, regml(res, 8))

                    m_cid = parser_lib.get_cid(medic_sid)
                    if m_cid in self._players and self._players[m_cid].current_class() != "engineer":
                        self.insert_player_class(medic_sid, "medic")

                    self.stat_upsert(self.STAT_TABLE, "overhealing_done", medic_sid, medic_name, medic_overhealing)
                    self.stat_upsert(self.STAT_TABLE, "overhealing_received", healt_sid, healt_name, medic_overhealing)

                    return

                #healing done
                #"vsn.RynoCerus<6><STEAM_0:0:23192637><Blue>" triggered "healed" against "Hyperbrole<3><STEAM_0:1:22674758><Blue>" (healing "26")
                res = regex(parser_lib.healing_done, logdata)
                if res:
                    #print "Healing done"
                    #pprint(res.groups())

                    medic_sid = regml(res, 3)
                    medic_name = parser_lib.escapePlayerString(regml(res, 1))
                    medic_healing = int(regml(res, 9))
                    medic_points = round(medic_healing / 600, 2)

                    healt_name = parser_lib.escapePlayerString(regml(res, 5))
                    healt_sid = regml(res, 7)

                    self.insert_player_team(medic_sid, regml(res, 4))
                    self.insert_player_team(healt_sid, regml(res, 8))

                    m_cid = parser_lib.get_cid(medic_sid)
                    if m_cid in self._players and self._players[m_cid].current_class() != "engineer":
                        self.insert_player_class(medic_sid, "medic")

                    self.stat_upsert(self.STAT_TABLE, "healing_done", medic_sid, medic_name, medic_healing)
                    self.stat_upsert(self.STAT_TABLE, "points", medic_sid, medic_name, medic_points)
                    self.stat_upsert(self.STAT_TABLE, "healing_received", healt_sid, healt_name, medic_healing)

                    return

                #item picked up
                #"skae<14><STEAM_0:1:31647857><Red>" picked up item "ammopack_medium"
                res = regex(parser_lib.item_pickup, logdata)
                if res:
                    #print "Item picked up"
                    #pprint(res.groups())

                    sid = regml(res, 3)
                    name = parser_lib.escapePlayerString(regml(res, 1))

                    colname = parser_lib.selectItemName(regml(res, 5))

                    if not colname:
                        return

                    self.stat_upsert(self.STAT_TABLE, colname, sid, name, 1) #add 1 to whatever item was picked up

                    return

                #player killed (normal)
                res = regex(parser_lib.player_kill, logdata)
                if res:
                    #print "Player killed (normal kill)"
                    #pprint(res.groups())
                    k_sid = regml(res, 3)
                    k_name = parser_lib.escapePlayerString(regml(res, 1))
                    k_pos = regml(res, 10)
                    k_weapon = regml(res, 9)

                    v_sid = regml(res, 7)
                    v_name = parser_lib.escapePlayerString(regml(res, 5))
                    v_pos = regml(res, 11)

                    self.insert_player_team(k_sid, regml(res, 4))
                    self.insert_player_team(v_sid, regml(res, 8))
                    self.detect_player_class(k_sid, k_weapon) #update class before inserting anything, so we can be sure that the data is going to the right class

                    #killer stats
                    self.stat_upsert(self.STAT_TABLE, "kills", k_sid, k_name, 1) #add kill to killer stat
                    self.stat_upsert(self.STAT_TABLE, "points", k_sid, k_name, 1) #add point to killer
         
                    #victim stats
                    self.stat_upsert(self.STAT_TABLE, "deaths", v_sid, v_name, 1) #add death to victim stat

                    # insert kill event into kill event table, NOT the generic event table
                    event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type, kill_attacker_id, kill_attacker_pos, kill_victim_id, kill_victim_pos) VALUES (E'%s', E'%s', E'%s', E'%s', E'%s', E'%s', E'%s')" % (
                                                    self.KILL_EVENT_TABLE, self.UNIQUE_IDENT, event_time, "kill", parser_lib.get_cid(k_sid), k_pos, parser_lib.get_cid(v_sid), v_pos) #creates a new, unique eventid with details of the event
                    self.execute_query(event_insert_query)

                    return

                #player killed (special kill) 
                #"Liquid'Time<41><STEAM_0:1:19238234><Blue>" killed "[v3] Roight<53><STEAM_0:0:8283620><Red>" with "knife" (customkill "backstab") (attacker_position "-1085 99 240") (victim_position "-1113 51 240")
                res = regex(parser_lib.player_kill_special, logdata)
                if res:
                    #print "Player killed (customkill)"
                    #pprint(res.groups())
            
                    ck_type = regml(res, 10)

                    if (ck_type == "feign_death"):
                        return
                
                    event_type = "kill_custom"
                
                    k_sid = regml(res, 3)
                    k_name = parser_lib.escapePlayerString(regml(res, 1))
                    k_pos = regml(res, 11)
                    k_weapon = regml(res, 9)

                    v_sid = regml(res, 7)
                    v_name = parser_lib.escapePlayerString(regml(res, 5))
                    v_pos = regml(res, 12)

                    self.insert_player_team(k_sid, regml(res, 4))
                    self.insert_player_team(v_sid, regml(res, 8))
                    self.detect_player_class(k_sid, k_weapon)

                    self.stat_upsert(self.STAT_TABLE, "kills", k_sid, k_name, 1)

                    if (ck_type == "backstab"):
                        self.insert_player_class(k_sid, "spy")
                        self.stat_upsert(self.STAT_TABLE, "backstabs", k_sid, k_name, 1)
                        self.stat_upsert(self.STAT_TABLE, "points", k_sid, k_name, 2)

                        event_type = "kill_custom_backstab"
                    elif (ck_type == "headshot"):
                        self.insert_player_class(k_sid, "sniper")

                        if not self._using_supstats:
                            self.stat_upsert(self.STAT_TABLE, "headshots", k_sid, k_name, 1)

                        self.stat_upsert(self.STAT_TABLE, "points", k_sid, k_name, 1.5)

                        event_type = "kill_custom_headshot"
                    else:
                        #print "ERROR: UNKNOWN CUSTOM KILL TYPE \"%s\"" % ck_type
                        
                        return

                    event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type, kill_attacker_id, kill_attacker_pos, kill_victim_id, kill_victim_pos) VALUES (E'%s', E'%s', '%s', E'%s', E'%s', E'%s', E'%s')" % (
                                                    self.KILL_EVENT_TABLE, self.UNIQUE_IDENT, event_time, event_type, parser_lib.get_cid(k_sid), k_pos, parser_lib.get_cid(v_sid), v_pos)
                    self.execute_query(event_insert_query)
                    
                    return
                
                #player assist
                #"Iyvn<40><STEAM_0:1:41931908><Blue>" triggered "kill assist" against "[v3] Kaki<51><STEAM_0:1:35387674><Red>" (assister_position "-905 -705 187") (attacker_position "-1246 -478 237") (victim_position "-1221 -53 283")
                res = regex(parser_lib.player_assist, logdata)
                if res:
                    #print "Player assisted in kill"
                    #pprint(res.groups())
                    a_sid = regml(res, 3)
                    a_name = parser_lib.escapePlayerString(regml(res, 1))
                    a_pos = regml(res, 9)

                    #increment stats!
                    self.stat_upsert(self.STAT_TABLE, "assists", a_sid, a_name, 1)
                    self.stat_upsert(self.STAT_TABLE, "points", a_sid, a_name, 0.5)

                    #kill assist ALWAYS (99.9999999999999%) comes after a kill, so we use the previous event id from inserting the kill into the event table. might need to change later
                    assist_update_query = "UPDATE %s SET kill_assister_id = E'%s', kill_assister_pos = E'%s' WHERE (eventid = (SELECT eventid FROM %s WHERE event_type = 'kill' and log_ident = E'%s' ORDER BY eventid DESC LIMIT 1)) AND log_ident = E'%s'" % (
                                                self.KILL_EVENT_TABLE, parser_lib.get_cid(a_sid), a_pos, self.KILL_EVENT_TABLE, self.UNIQUE_IDENT, self.UNIQUE_IDENT)
                    self.execute_query(assist_update_query)

                    self.insert_player_team(a_sid, regml(res, 4))

                    return

                #medic death ubercharge = 0 or 1, healing = amount healed in that life. kill message comes directly after
                #"%s<%i><%s><%s>" triggered "medic_death" against "%s<%i><%s><%s>" (healing "%d") (ubercharge "%s")
                res = regex(parser_lib.medic_death, logdata)
                if res:
                    #print "Medic death"
                    #pprint(res.groups())
                    m_sid = regml(res, 7)
                    m_name = parser_lib.escapePlayerString(regml(res, 5))
                    m_healing = int(regml(res, 9))
                    m_uberlost = int(regml(res, 10))

                    # only go into the queue if uber is lost. fuck yea optimisation!
                    if m_uberlost > 0:
                        self.stat_upsert(self.STAT_TABLE, "ubers_lost", m_sid, m_name, m_uberlost)
            
                    #put medic_death info into event table
                    event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type, medic_steamid, medic_uber_lost, medic_healing) VALUES (E'%s', E'%s', '%s', E'%s', '%s', '%s')" % (self.MEDIC_EVENT_TABLE, 
                                                           self.UNIQUE_IDENT, event_time, "medic_death", parser_lib.get_cid(m_sid), m_uberlost, m_healing)
                    self.execute_query(event_insert_query)

                    return

                #ubercharge used
                res = regex(parser_lib.uber_used, logdata)
                if res:
                    #print "Ubercharge used"
                    #pprint(res.groups())
                    m_sid = regml(res, 3)
                    m_name = parser_lib.escapePlayerString(regml(res, 1))

                    self.stat_upsert(self.STAT_TABLE, "ubers_used", m_sid, m_name, 1)

                    event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type, medic_steamid, medic_uber_used) VALUES (E'%s', E'%s', '%s', E'%s', '%s')" % (self.MEDIC_EVENT_TABLE, 
                                                            self.UNIQUE_IDENT, event_time, "uber_used", parser_lib.get_cid(m_sid), 1)
                    self.execute_query(event_insert_query)

                    return

                #domination
                res = regex(parser_lib.player_dominated, logdata)
                if res:
                    #print "Player dominated"
                    #pprint(res.groups())

                    p_sid = regml(res, 3)
                    p_name = parser_lib.escapePlayerString(regml(res, 1))

                    v_sid = regml(res, 7)
                    v_name = parser_lib.escapePlayerString(regml(res, 5))

                    self.stat_upsert(self.STAT_TABLE, "dominations", p_sid, p_name, 1)
                    self.stat_upsert(self.STAT_TABLE, "times_dominated", v_sid, v_name, 1)


                    return

                #revenge
                res = regex(parser_lib.player_revenge, logdata)
                if res:
                    #print "Player got revenge"
                    #pprint(res.groups())

                    p_sid = regml(res, 3)
                    p_name = parser_lib.escapePlayerString(regml(res, 1))

                    self.stat_upsert(self.STAT_TABLE, "revenges", p_sid, p_name, 1)

                    return

                # self-kill suicide
                res = regex(parser_lib.player_suicide, logdata)
                if res:
                    #print "Player committed suicide"
                    #pprint(res.groups())
                    
                    p_sid = regml(res, 3)
                    p_name = parser_lib.escapePlayerString(regml(res, 1))

                    self.insert_player_team(p_sid, regml(res, 4))
                    self.detect_player_class(p_sid, regml(res, 5))
                    
                    self.stat_upsert(self.STAT_TABLE, "suicides", p_sid, p_name, 1)
                    self.stat_upsert(self.STAT_TABLE, "deaths", p_sid, p_name, 1)
                    
                    return

                # environment-kill suicide
                res = regex(parser_lib.player_suicide_custom, logdata)
                if res:
                    #print "Player committed suicide"
                    #pprint(res.groups())

                    p_sid = regml(res, 3)
                    p_name = parser_lib.escapePlayerString(regml(res, 1))

                    self.insert_player_team(p_sid, regml(res, 4))

                    self.stat_upsert(self.STAT_TABLE, "suicides", p_sid, p_name, 1)
                    self.stat_upsert(self.STAT_TABLE, "deaths", p_sid, p_name, 1)

                    return
                    
                #engi building destruction
                #"dcup<109><STEAM_0:0:15236776><Red>" triggered "killedobject" (object "OBJ_SENTRYGUN") (weapon "tf_projectile_pipe") (objectowner "NsS. oLiVz<101><STEAM_0:1:15674014><Blue>") (attacker_position "551 2559 216")
                res = regex(parser_lib.building_destroyed, logdata)
                if res:
                    #print "Player destroyed engineer building"
                    #pprint(res.groups())

                    p_sid = regml(res, 3)
                    p_name = parser_lib.escapePlayerString(regml(res, 1))

                    self.insert_player_team(p_sid, regml(res, 4))
                    self.detect_player_class(p_sid, regml(res, 7))

                    self.stat_upsert(self.STAT_TABLE, "buildings_destroyed", p_sid, p_name, 1)
                    self.stat_upsert(self.STAT_TABLE, "points", p_sid, p_name, 1)

                    return

                #engi building creation
                #"|S| ynth<13><STEAM_0:1:2869609><Red>" triggered "builtobject" (object "OBJ_TELEPORTER") (position "-4165 1727 -511")
                res = regex(parser_lib.building_created, logdata)
                if res:
                    #user is obv an engineer if he's building shit!
                    sid = regml(res, 3)

                    self.insert_player_team(sid, regml(res, 4))
                    self.insert_player_class(sid, "engineer")
                    
                    return

            #end round_pause blocking
            
            #chat
            #"Console<0><Console><Console>" say "blah"
            res = regex(parser_lib.chat_message, logdata)
            if res:
                #print "Chat was said"
                #pprint(res.groups())

                c_sid = regml(res, 3)
                if c_sid == "Console" or c_sid == "0":
                    c_sid = "STEAM_0:0:0"

                c_sid = parser_lib.get_cid(c_sid) #get community id of steamid
                c_name = parser_lib.escapePlayerString(regml(res, 1))
                c_team = regml(res, 4)

                chat_type = regml(res, 5)
                chat_message = parser_lib.escapePlayerString(regml(res, 6))

                event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type) VALUES (E'%s', E'%s', '%s')" % (self.EVENT_TABLE, self.UNIQUE_IDENT, event_time, "chat")
                self.execute_query(event_insert_query)

                chat_insert_query = "INSERT INTO %s (log_ident, steamid, name, team, chat_type, chat_message) VALUES ('%s', E'%s', E'%s', '%s', '%s', E'%s')" % (self.CHAT_TABLE, 
                                                        self.UNIQUE_IDENT, c_sid, c_name, c_team, chat_type, chat_message)

                self.execute_query(chat_insert_query, queue_priority = queryqueue.HIPRIO)

                return
            
            #point capture
            #/Team "(Blue|Red)" triggered "pointcaptured" \x28cp "(\d+)"\x29 \x28cpname "(.+)"\x29 \x28numcappers "(\d+)".+/
            #Team "Red" triggered "pointcaptured" (cp "0") (cpname "#koth_viaduct_cap") (numcappers "5") (player1 "[v3] Faithless<47><STEAM_0:0:52150090><Red>") (position1 "-1370 59 229") 
            #(player2 "[v3] Chrome<48><STEAM_0:1:41365809><Red>") (position2 "-1539 87 231") (player3 "[v3] Jak<49><STEAM_0:0:18518582><Red>") 
            #(position3 "-1659 150 224") (player4 "[v3] Kaki<51><STEAM_0:1:35387674><Red>") (position4 "-1685 146 224") 
            #(player5 "[v3] taintedromance<52><STEAM_0:0:41933053><Red>") (position5 "-1418 182 236")
            res = regex(parser_lib.point_capture, logdata)
            if res:
                #print "Point captured"
                #pprint(res.groups())
                #this is going to be tricky
                cap_team = regml(res, 1)
                cap_name = parser_lib.escapePlayerString(regml(res, 3))
                num_cappers = regml(res, 4)
                
                event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type, capture_name, capture_team, capture_num_cappers) VALUES (E'%s', E'%s', '%s', E'%s', '%s', '%s')" % (self.EVENT_TABLE,
                                                    self.UNIQUE_IDENT, event_time, "point_capture", cap_name, cap_team, num_cappers)

                #self.execute_query(event_insert_query)

                #INPUT: (player2 "[v3] Chrome<48><STEAM_0:1:41365809><Red>")
                capper_re = re.compile(r'\x28player(\d) "(.*?)<(\d+)><(.*?)><(Red|Blue)>"')
                #OUTPUT: ('2', '[v3] Chrome', '48', 'STEAM_0:1:41365809', 'Red')            

                for capper in capper_re.finditer(logdata):
                    #print "Capper:"
                    #pprint(capper.groups())

                    c_sid = regml(capper, 4)
                    c_name = parser_lib.escapePlayerString(regml(capper, 2))

                    self.stat_upsert(self.STAT_TABLE, "captures", c_sid, c_name, 1)
                    self.stat_upsert(self.STAT_TABLE, "points", c_sid, c_name, 2)

                return

            #capture block
            #"pvtx<103><STEAM_0:1:7540588><Red>" triggered "captureblocked" (cp "1") (cpname "Control Point B") (position "-2143 2284 156")
            res = regex(parser_lib.capture_blocked, logdata)
            if res:
                #print "Capture blocked"
                #pprint(res.groups())

                cb_sid = regml(res, 3)
                cb_name = parser_lib.escapePlayerString(regml(res, 1))

                self.stat_upsert(self.STAT_TABLE, "captures_blocked", cb_sid, cb_name, 1)
                self.stat_upsert(self.STAT_TABLE, "points", cb_sid, cb_name, 1)

                cap_name = parser_lib.escapePlayerString(regml(res, 6))
                cap_block_team = regml(res, 4)

                #re-use the capture event columns, but this time capture_blocked is 1 instead of NULL, so we can distinguish
                event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type, capture_name, capture_team, capture_blocked) VALUES (E'%s', E'%s', '%s', E'%s', '%s', '%s')" % (self.EVENT_TABLE,
                                                        self.UNIQUE_IDENT, event_time, "point_capture_block", cap_name, cap_block_team, 1)
                self.execute_query(event_insert_query)

                return

            #"b1z<19><STEAM_0:0:18186373><Red>" joined team "Blue"
            res = regex(parser_lib.player_team_join, logdata)
            if res:
                team = regml(res, 5)

                if team == "Spectator" or team == "None" or team is None:
                    return

                sid = regml(res, 3)

                if sid != "BOT":
                    self.insert_player_team(sid, team.lower())

                return
                
            #current score (shown after round win/round length)
            #L 10/21/2012 - 01:23:48: World triggered "Round_Win" (winner "Blue")
            #L 10/21/2012 - 01:23:48: World triggered "Round_Length" (seconds "88.26")
            #L 10/21/2012 - 01:23:48: Team "Red" current score "0" with "6" players
            #L 10/21/2012 - 01:23:48: Team "Blue" current score "4" with "6" players
            res = regex(parser_lib.team_score, logdata)
            if res:
                #print "Current scores"
                #pprint(res.groups())

                team = regml(res, 1)
                t_score = regml(res, 2)
                #t_players = regml(res, 3)

                #use previous round_win event id
                event_update_query = "UPDATE %s SET round_%s_score = '%s' WHERE (eventid = (SELECT eventid FROM %s WHERE event_type = 'round_end' AND log_ident = '%s' ORDER BY eventid DESC LIMIT 1)) AND log_ident = '%s'" % (self.EVENT_TABLE, 
                                                        team.lower(), t_score, self.EVENT_TABLE, self.UNIQUE_IDENT, self.UNIQUE_IDENT)

                self.execute_query(event_update_query)
                
                self.ROUND_PAUSE = True

                return

            #game over
            res = regex(parser_lib.game_over, logdata)
            if res:
                #print "Game over"
                #pprint(res.groups())
            
                go_reason = regml(res, 1)

                event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type, game_over_reason) VALUES (E'%s', E'%s', '%s', E'%s')" % (self.EVENT_TABLE, self.UNIQUE_IDENT, event_time, "game_over", go_reason)
                self.execute_query(event_insert_query)
                
                return

            #final scores always comes after game_over
            res = regex(parser_lib.final_team_score, logdata)
            if res:
                #print "Final scores"
                #pprint(res.groups())

                fs_team = regml(res, 1).lower()
                fs_score = regml(res, 2)
                
                final_score_query = "UPDATE %s SET round_%s_score = '%s' WHERE event_type = 'game_over' and log_ident = '%s'" % (self.EVENT_TABLE, fs_team, fs_score, self.UNIQUE_IDENT)
                self.execute_query(final_score_query)

                self._have_final_scores[fs_team] = True

                if self._have_final_scores["red"] and self._have_final_scores["blue"]:
                    self.GAME_OVER = True
                    self.endLogParsing(True)
                
                return

            res = regex(parser_lib.player_name_change, logdata)
            if res:
                #print player name change
                return

            #rcon command
            res = regex(parser_lib.rcon_command, logdata)
            if res:
                #print "Someone issued rcon command"
                #pprint(res.groups())

                return

            res = regex(parser_lib.server_cvar_value, logdata)
            if res:

                return

            #disconnect RL 10/07/2012 - 01:13:44: "triple h<162><STEAM_0:1:33713004><Red>" disconnected (reason " #tf2pug")
            res = regex(parser_lib.player_disconnect, logdata)
            if res:
                #print "Player disconnected"
                #pprint(res.groups())
                
                return
            
            #connect RL 10/07/2012 - 22:45:11: "GU | wm<3><STEAM_0:1:7175436><>" connected, address "124.168.51.7:27005"
            res = regex(parser_lib.player_connect, logdata)
            if res:
                #print "Player connected"
                #pprint(res.groups())

                return

            #validated "hipsterhipster<4><STEAM_0:1:22674758><>" STEAM USERID validated
            res = regex(parser_lib.player_validated, logdata)
            if res:
                #print "Player validated"
                #pprint(res.groups())

                return

            res = regex(parser_lib.player_entered_game, logdata)
            if res:
                return

            # player spawn
            #"snips<3><STEAM_0:1:43598512><Red>" spawned as "Sniper"
            res = regex(parser_lib.player_spawn, logdata)
            if res:
                # we now know exactly what class this player is
                sid = regml(res, 3)
                team = regml(res, 4)
                pclass = regml(res, 5).lower()

                if pclass == "undefined" or team == "unknown":
                    return

                self.insert_player_team(sid, team)

                if pclass not in spawn_swap_classes:
                    self.insert_player_class(sid, pclass)

                return

            #class change
            res = regex(parser_lib.player_class_change, logdata)
            if res:
                #print "Player changed class"
                #pprint(res.groups())

                #NOW WE ADD CLASSES O GOD
                pclass = regml(res, 5)
                sid = regml(res, 3)
                team = regml(res, 4)

                self.insert_player_team(sid, team)

                if pclass not in spawn_swap_classes:
                    self.insert_player_class(sid, pclass)

                return

            #round win
            res = regex(parser_lib.round_win, logdata)
            if res:
                #print "Round won"
                #pprint(res.groups())

                event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type) VALUES (E'%s', E'%s', '%s')" % (self.EVENT_TABLE, self.UNIQUE_IDENT, event_time, "round_end")

                self.execute_query(event_insert_query)

                self.ROUND_PAUSE = True

                return

            #overtime
            res = regex(parser_lib.round_overtime, logdata)
            if res:
                #print "Overtime"
                #pprint(res.groups())

                #event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type) VALUES (E'%s', E'%s', '%s')" % (self.EVENT_TABLE, self.UNIQUE_IDENT, event_time, "round_overtime")

                #self.execute_query(event_insert_query)

                return

            #round length
            #World triggered "Round_length" \x28seconds "(\d+)\.(\d+)"\x29
            res = regex(parser_lib.round_length, logdata)
            if res:
                #print "Round length"
                #pprint(res.groups())
        
                r_length = "%s.%s" % (regml(res, 1), regml(res, 2))

                event_update_query = "UPDATE %s SET round_length = '%s' WHERE (eventid = (SELECT eventid FROM %s WHERE event_type = 'round_end' and log_ident = '%s' ORDER BY eventid DESC LIMIT 1)) AND log_ident = '%s'" % (self.EVENT_TABLE, 
                                                                    r_length, self.EVENT_TABLE, self.UNIQUE_IDENT, self.UNIQUE_IDENT)

                self.execute_query(event_update_query)

                self.ROUND_PAUSE = True

                return
                
            #round start
            res = regex(parser_lib.round_start, logdata)
            if res:
                #print "Round start"
                #pprint(res.groups())

                #event_insert_query = "INSERT INTO %s (log_ident, event_time, event_type) VALUES (E'%s', E'%s', '%s')" % (self.EVENT_TABLE, self.UNIQUE_IDENT, event_time, "round_start")
                #self.execute_query(event_insert_query)

                # we use this variable so we know if we've received a round_start before a LIVELOG_LOGGING_START
                # it only needs to be set to True before LIVELOG_LOGGING_START and we'll know that we don't 
                # need to add a Round_start message to the log file if we receive a LIVELOG_LOGGING_START
                self._first_round_started = True

                # end round pause, because new round
                self.ROUND_PAUSE = False
                
                return
                
            #setup end UNUSED
            res = regex(parser_lib.round_setup_end, logdata)
            if res:
                #print "Round Setup End"
                #pprint(res.groups())

                return
            
            #mini round win
            res = regex(parser_lib.mini_round_win, logdata)
            if res:
                #print "Mini round win"
                #pprint(res.groups())

                return

            #mini round length
            res = regex(parser_lib.mini_round_length, logdata)
            if res:
                #print "Mini round length"
                #pprint(res.groups())

                return

            res = regex(parser_lib.mini_round_start, logdata)
            if res:
                return

            res = regex(parser_lib.mini_round_selected, logdata)
            if res:
                return


            res = regex(parser_lib.map_change, logdata)
            if res:
                self.logger.info("Map changed to %s. Ending this log", regml(res, 1))

                self.GAME_OVER = True
                self.endLogParsing(True)

                return

            regex_match = parser_lib.ParserRegexHelper.match_expression(logdata)
            if regex_match is None:
                self.logger.debug("Reached end of regex checks with no match. Log data: %s", logdata)

        except Exception, e:
            self.logger.exception("Exception parsing log data: %s", logdata)

    def stat_upsert(self, table, column, steamid, name, value):
        #takes all the data that would usually go into an upsert, allows for cleaner code in the regex parsing

        # ignore zero values. it's more efficient if we handle them here
        if (value <= 0) or (isinstance(value, str) and int(value) == 0):
            return

        cid = parser_lib.get_cid(steamid) #convert steamid to community id
        if cid == "BOT":
            return

        name = name[:30] #max length of 30 characters for names        
        self.add_player(cid, name = name) #get this guy a player_data object!
        
        self.insert_player_details(cid, name)

        insert_query = "INSERT INTO %s (log_ident, steamid, %s, class) VALUES (E'%s', E'%s', E'%s', E'%s')" % (self.STAT_TABLE, column, 
                                        self.UNIQUE_IDENT, cid, value, self._players[cid].current_class())

        update_query = "UPDATE %s SET %s = COALESCE(%s, 0) + %s WHERE (log_ident = '%s' AND steamid = E'%s' AND class = '%s')" % (self.STAT_TABLE, column, 
                                                column, value, self.UNIQUE_IDENT, cid, self._players[cid].current_class())

        self.execute_upsert(insert_query, update_query)

    # insert_player_team(steamid, team)
    # Takes a steamid in the format STEAM_x:x:xxxx* and a team.
    # Updates records matching the SteamID with the given team
    def insert_player_team(self, a_sid, a_team):
        a_team = a_team.lower() #make sure the team is lowercase
        a_cid = parser_lib.get_cid(a_sid)

        if a_cid == "BOT":
            return

        if self.add_player(a_cid, team = a_team):
            # new player. we should insert him into the database
            insert_query = "INSERT INTO %s (log_ident, steamid, class, team) VALUES (E'%s', E'%s', E'%s', E'%s')" % (
                                self.STAT_TABLE, self.UNIQUE_IDENT, a_cid, self._players[a_cid].current_class(), a_team)

            # insert new entry asap. should be done before stat_upsert
            self.execute_query(insert_query, queue_priority = queryqueue.HIPRIO)

            team_to_insert = True

        elif not self._players[a_cid].is_team_same(a_team):
            # the team differs from the known team, so we should update it to this new value
            self._players[a_cid].set_team(a_team)

            update_query = "UPDATE %s SET team = E'%s' WHERE log_ident = '%s' AND steamid = E'%s'" % (
                            self.STAT_TABLE, a_team, self.UNIQUE_IDENT, a_cid)

            # team update can be done at a leisurely pace
            self.execute_query(update_query)

    # insert_player_class(steamid, class)
    # Takes a steamid in the format STEAM_x:x:xxxx* and a class
    # Inserts the class into the datatabase for that ID if the player
    # is not already marked as having played that class. Also sets
    # current class
    def insert_player_class(self, sid, pclass):
        cid = parser_lib.get_cid(sid)

        if cid == "BOT":
            return
        
        if cid in self._players:
            pdata = self._players[cid]
            current_class = pdata.current_class()

            #self.logger.debug("Player '%s' is in players dict. Current team: %s, current class: %s, all classes: %s",
            #                            cid, pdata.current_team(), current_class, pdata.class_list())

            if (current_class == "UNKNOWN") or (len(pdata.class_list()) == 0):
                # this is the first class insertion for this player, so we add
                # the class and update any previous UNKNOWN records
                pdata.add_class(pclass)

                #if the class was inserted as unknown, it is likely that the 'unknown' class is now this class. this is what we'll assume, anyway
                update_query = "UPDATE %s SET class = '%s' WHERE (log_ident = '%s' AND steamid = E'%s' AND class = 'UNKNOWN')" % (
                                    self.STAT_TABLE, pclass, self.UNIQUE_IDENT, cid)

                # update the class
                self.execute_query(update_query)

            elif not pdata.class_played(pclass):
                # class has not been played. we need to add it
                pdata.add_class(pclass)

                insert_query = "INSERT INTO %s (log_ident, steamid, class, team) VALUES (E'%s', E'%s', E'%s', E'%s')" % (
                                    self.STAT_TABLE, self.UNIQUE_IDENT, cid, pclass, pdata.current_team())

                # insert into db
                self.execute_query(insert_query)

            elif current_class != pclass:
                # class has been played before and it is not unknown, so set current class to the new class
                pdata.set_class(pclass)
                

    # insert_player_details(communityid, name)
    # Inserts a player into the database with the given name, and the
    # current log ident. If the name is different from the previous
    # known name, it will be updated.
    def insert_player_details(self, cid, name):
        if cid == "BOT":
            return

        if name:
            details_query = None

            if self.add_player(cid, name = name) or not self._players[cid].details_inserted:
                #player just added, need to insert into details table
                details_query = "INSERT INTO %s (steamid, log_ident, name) VALUES ('%s', '%s', E'%s')" % (self.PLAYER_TABLE,
                                    cid, self.UNIQUE_IDENT, name)

            elif not self._players[cid].is_name_same(name):
                #else if name changed, need to update
                details_query = "UPDATE %s SET name = E'%s' WHERE log_ident = '%s' AND steamid = E'%s'" % (self.PLAYER_TABLE,
                                    name, self.UNIQUE_IDENT, cid)

                self._players[cid].set_name(name)

            if details_query:
                self._players[cid].details_inserted = True
                self.execute_query(details_query, queue_priority = queryqueue.HIPRIO)

    def add_player(self, cid, pclass=None, name=None, team=None):
        if cid == "BOT":
            return

        if cid not in self._players:
            self._players[cid] = parser_lib.PlayerData(pclass, name, team)
            
            self.insert_player_details(cid, name)

            return True
        else:
            return False

    def detect_player_class(self, sid, weapon):
        #take weapon name, and try to match it to a class name
        #print "checking weapon %s" % weapon

        cid = parser_lib.get_cid(sid)
        if cid == "BOT":
            return

        for pclass in self._weapon_data:
            if weapon in self._weapon_data[pclass]: #player's weapon matches this classes' weapon data
                if self._players[cid].current_class() != pclass:
                    self.insert_player_class(sid, pclass) #add this class to the database

                break

    def execute_upsert(self, insert_query, update_query, conn=None, curs=None, close=True, use_queue=True, queue_priority = queryqueue.NMPRIO):
        if use_queue:
            self.add_qtq(insert_query, update_query, priority = queue_priority)
        
        else:
            if not self.db.closed:
                if not conn:
                    conn = self.__get_db_conn()
                    if not conn:
                        return

                if not curs:
                    curs = self.__get_conn_cursor(conn)
                    if not curs:
                        return

                try:
                    curs.execute("SELECT pgsql_upsert(%s, %s)", (insert_query, update_query,))

                    conn.commit()

                except:
                    self.logger.exception("Error executing upsert. INSERT: %s, UPDATE: %s", insert_query, update_query)
                    conn.rollback()

                finally:
                    if close:
                        self.__close_db_components(conn = conn, cursor = curs)

    def execute_query(self, query, curs=None, conn=None, close=True, use_queue=True, queue_priority = queryqueue.NMPRIO):
        if use_queue:
            self.add_qtq(query, priority = queue_priority)
        
        else:
            try:
                if not self.db.closed:
                    if not conn:
                        conn = self.__get_db_conn()
                        if not conn: #if we still can't get a connection, return
                            return

                    if not curs:
                        curs = self.__get_conn_cursor(conn)
                        if not curs: #if we still can't get a cursor, return
                            return
                        
                    try:
                        curs.execute(query)
                        conn.commit()
                    except psycopg2.DataError, e:
                        self.logger.exception("DB DATA ERROR INSERTING DATA %s", query)
                        
                        conn.rollback()
                    except Exception, e:
                        self.logger.exception("DB ERROR")
                        
                        conn.rollback()
                    finally:
                        if close:
                            self.__close_db_components(conn = conn, cursor = curs)
                    
                else:
                    self.logger.info("NOTICE: DATABASE CONNECTION POOL IS CLOSED")
                    if close:
                        self.__close_db_components(conn = conn, cursor = curs)

            except:
                self.logger.exception("Exception occurred rolling back the connection")
                if close:
                    self.__close_db_components(conn = conn, cursor = curs)

    def add_qtq(self, query_a, query_b=None, priority=queryqueue.NMPRIO):
        # add query to the queue with priority
        # the queue processor will automatically handle double queries as an
        # upsert
        self._master_query_queue.add_query(query_a, query_b, priority) 


    def all_users_are_bots(self):
        if self.__time_elapsed() > 300 and len(self._players) == 0:
            return True

        else:
            return False

    def endLogParsing(self, game_over=False, shutdown=False):
        self.__end_log_lock.acquire() #lock end log parsing, so it cannot be done by multiple threads at once
        
        try:
            if not self.LOG_PARSING_ENDED:
                self.logger.info("Ending log parsing")
                self.LOG_PARSING_ENDED = True

                if not self.HAD_ERROR:
                    if (len(self._players) < 2) or (self.__time_elapsed() < 60):
                        """
                        If the player dict length is < 2 (i.e, less than 2 players in the server) or there has been less than 60 seconds elapsed,
                        this log is considered invalid and is to be deleted
                        """
                        end_query = "DELETE FROM %(index)s WHERE log_ident = '%(logid)s'; DELETE FROM %(stable)s WHERE log_ident = '%(logid)s'; DELETE FROM %(ptable)s WHERE log_ident = '%(logid)s'" % {
                                "index": self.INDEX_TABLE,
                                "stable": self.STAT_TABLE,
                                "ptable": self.PLAYER_TABLE,
                                "logid": self.UNIQUE_IDENT
                            }
                            
                        if shutdown:
                            self.execute_query(end_query, use_queue=False) #skip the queue for the end query, because we are shutting down
                        else:
                            self.execute_query(end_query, queue_priority = queryqueue.HIPRIO) #want this log deleted ASAP!

                        self.logger.info("No data in this log. Tables have been deleted")

                    else:
                        #sets live to false
                        live_end_query = "UPDATE %s SET live = false WHERE log_ident = E'%s'" % (self.INDEX_TABLE, self.UNIQUE_IDENT)

                        if shutdown:
                            self.execute_query(live_end_query, use_queue=False) #skip the queue
                        else:
                            self.execute_query(live_end_query, queue_priority = queryqueue.NMPRIO)
                    
                    self._close_log_file()

                    if self.closeListenerCallback is not None and game_over:
                        self.closeListenerCallback(game_over)

        except:
            self.logger.exception("Exception ending log")

        self.__end_log_lock.release()

    def write_to_log(self, data):
        try:
            self.__get_file_lock()
            if self.LOG_FILE_HANDLE and not self.LOG_FILE_HANDLE.closed:
                self.LOG_FILE_HANDLE.write(data)

                self._log_file_writes += 1

                if (self._log_file_writes % 200) == 0:
                    #force a flush to disk every 200 writes, to reduce buffer usage
                    self.LOG_FILE_HANDLE.flush()
                    os.fsync(self.LOG_FILE_HANDLE.fileno())
        except:
            self.logger.exception("Exception writing to log file")
        finally:
            self.__release_file_lock()

    def _close_log_file(self):
        try:
            self.__get_file_lock()

            if self.LOG_FILE_HANDLE and not self.LOG_FILE_HANDLE.closed:
                # write a log file closed message, so we keep the same log file structure as the server does
                # this will help when users want to use other 3rd party log parsers with this log file
                if self._last_event_times:
                    self.LOG_FILE_HANDLE.write("L %s - %s: Log file closed\n" % self._last_event_times)

                self.LOG_FILE_HANDLE.write("\n") #add a new line before EOF

            self.LOG_FILE_HANDLE.close()
                
        except:
            self.logger.exception("Exception closing the log file")

        finally:
            self.__release_file_lock()

    def __cleanup(self, conn=None, cursor=None):
        #for cleaning up after init error
        self._close_log_file()

        if cursor:
            if not cursor.closed:
                cursor.close()

        if conn:
            if not self.db.closed:
                self.db.putconn(conn)

    def __get_db_conn(self):
        conn = None
        if not self.db.closed:
            try:
                conn = self.db.getconn()
            except:
                self.logger.exception("Unable to get database connection from pool")

        return conn

    def __get_conn_cursor(self, conn):
        cursor = None
        if not conn.closed:
            try:
                cursor = conn.cursor()
            except:
                self.logger.exception("Unable to get cursor from db connection")

        return cursor

    def __close_db_components(self, conn=None, cursor=None):
        if not self.db.closed:
            if cursor and not cursor.closed:
                cursor.close()

            if conn:
                self.db.putconn(conn)

    def __get_file_lock(self):
        self.__log_file_lock.acquire()

    def __release_file_lock(self):
        self.__log_file_lock.release()

    def __time_elapsed(self):
        return time.time() - self.__start_time

