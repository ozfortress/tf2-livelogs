try:
    import psycopg2
except ImportError:
    print """You are missing psycopg2.
    Install using `pip install psycopg2` or visit http://initd.org/psycopg/
    """
    quit()

import time
import struct
import socket
import re
import os
import threading
from HTMLParser import HTMLParser

import logging
import logging.handlers

from pprint import pprint

import parser_regex


"""log_message_format = logging.Formatter(fmt="[(%(levelname)s) %(process)s %(asctime)s %(module)s:%(name)s:%(lineno)s] %(message)s", datefmt="%H:%M:%S")

log_file_handler = logging.handlers.TimedRotatingFileHandler("parser.log", when="midnight")
log_file_handler.setFormatter(log_message_format)
log_file_handler.setLevel(logging.DEBUG)"""

class parserClass():
    def __init__(self, unique_ident, server_address=None, current_map=None, log_name=None, log_uploaded=False, endfunc=None, webtv_port=None):
        #ALWAYS REQUIRE A UNIQUE IDENT, OTHER PARAMS ARE OPTIONAL
        self.HAD_ERROR = False
        self.LOG_FILE_HANDLE = None
        self.db = None

        self.logger = logging.getLogger(unique_ident)
        self.logger.setLevel(logging.DEBUG)

        import ConfigParser
        cfg_parser = ConfigParser.SafeConfigParser()
        if cfg_parser.read(r'll-config.ini'):
            try:
                db_host = cfg_parser.get('database', 'db_host')
                db_port = cfg_parser.getint('database', 'db_port')
                db_user = cfg_parser.get('database', 'db_user')
                db_pass = cfg_parser.get('database', 'db_password')
                db_name = cfg_parser.get('database', 'db_name')
                
                log_dir = cfg_parser.get('log-listener', 'log_directory')
                

                self._db_dsn = 'dbname=%s user=%s password=%s host=%s port=%s' % (
                            db_name, db_user, db_pass, db_host, db_port)
            except:
                self.logger.error("Unable to read options from config file")
                self.HAD_ERROR = True
                return
        else:
            self.logger.error("Error reading config file")
            
            self.HAD_ERROR = True
            return
            
        #try open the file before opening the sql connection, so if the file errors out we won't have to close the sql connection as well
        try:
            if not os.path.exists(log_dir):
                #need to make the directory
                os.makedirs(log_dir, 0755)
                
            log_file_name = "%s.log" % unique_ident
            log_file = os.path.normpath(os.path.join(log_dir, log_file_name))
            
            self.LOG_FILE_HANDLE = open(log_file, 'w')
            
        except OSError:
            self.logger.error("Error opening new log file for writing, or creating log directory: %s", OSError)
            
            self.HAD_ERROR = True
            return
            
        try:
            self.db = psycopg2.connect(self._db_dsn)

        except Exception, e:
            self.logger.exception("Had exception while trying to connect to psql database")
            
            self.HAD_ERROR = True
            
            self.LOG_FILE_HANDLE.close() #close the file handle previously established
            return
        
        self.closeListenerCallback = endfunc
        
        self.UNIQUE_IDENT = unique_ident
        self.GAME_OVER = False
        self.ROUND_PAUSE = False
        self.LOG_PARSING_ENDED = False
        self.RECONNECTING_TO_DATABASE = False

        self._using_livelogs_output = False

        self._query_queue = [] #a list of queryQueueDataObject objects, to be processed on a reconnect

        #if no map is specified (auto detect), set map to 0
        if (current_map == None):
            self.current_map = 0
        else:
            self.current_map = current_map

        if (webtv_port == None):
            webtv_port = 0
            
            
        self.logger.info("PARSER UNIQUE IDENT: " + self.UNIQUE_IDENT)
        
        dbCursor = self.db.cursor()
        try:
            dbCursor.execute("SELECT create_global_stat_table()")
            dbCursor.execute("SELECT setup_log_tables(%s)", (self.UNIQUE_IDENT,))

            if (server_address != None):
                dbCursor.execute("SELECT create_global_server_table()")
            
                if not log_name:
                    log_name = "log-%s" % time.strftime("%Y-%m-%d-%H-%M") #log-year-month-day-hour-minute
                
                dbCursor.execute("INSERT INTO livelogs_servers (server_ip, server_port, log_ident, map, log_name, live, webtv_port) VALUES (%s, %s, %s, %s, %s, 'true', %s)", 
                                            (self.ip2long(server_address[0]), str(server_address[1]), self.UNIQUE_IDENT, self.current_map, log_name, webtv_port,))

            self.db.commit()
        except:
            self.logger.exception("Exception during table init")

            self.HAD_ERROR = True

            dbCursor.close()
            self.db.close()

            self.LOG_FILE_HANDLE.close()

            return

        if (log_uploaded):
            #TODO: Create an indexing method for logs that were manually uploaded and parsed
            pass

        dbCursor.close()

        self.EVENT_TABLE = "log_event_%s" % self.UNIQUE_IDENT
        self.STAT_TABLE = "log_stat_%s" % self.UNIQUE_IDENT
        self.CHAT_TABLE = "log_chat_%s" % self.UNIQUE_IDENT

        self.ITEM_DICT = {
            'ammopack_small': 'ap_small',
            'ammopack_medium': 'ap_medium', 
            'tf_ammo_pack': 'ap_large', 
            'medkit_small': 'mk_small', 
            'medkit_medium': 'mk_medium', 
            'medkit_large': 'mk_large'
            }
            
        self.PLAYER_TEAMS = {}
        self._player_logs = {} #whether this user has been added to the log index or not
        
        self.logger.info("Parser initialised")

    def ip2long(self, ip):
        return struct.unpack('!L', socket.inet_aton(ip))[0]

    def long2ip(self, longip):
        return socket.inet_ntoa(struct.pack('L', longip))


    def parse(self, logdata):
        if not logdata or not self.db or self.GAME_OVER or self.HAD_ERROR or self.LOG_PARSING_ENDED:
            return

        try:
            event_time = None
            #self.logger.debug("PARSING LOG: %s", logdata)

            regex = self.regex #avoid having to use fucking self.regex every time (ANNOYING++++)
            regml = self.regml #local def for regml ^^^

            self.LOG_FILE_HANDLE.write(logdata + "\n")

            #if res:
            #    #print "Matching regex:"
            #    #pprint(res.groups())

            #log file start
            #RL 10/07/2012 - 01:13:34: Log file started (file "logs_pug/L1007104.log") (game "/games/tf2_pug/orangebox/tf") (version "5072")
            res = regex(parser_regex.log_file_started, logdata)
            if res:
                #print "Log file started"
                #pprint(res.groups())
                #do shit with log file name?
                
                return

            #log time
            res = regex(parser_regex.log_timestamp, logdata)
            if res:
                #print "Time of current log"
                #pprint(res.groups())
                
                event_time = "%s %s" % (regml(res, 1), regml(res, 2))
            
            if not event_time:
                return


            #log restart, sent when a mp_restartgame is issued (need a new log file, so we end this one)
            res = regex(parser_regex.game_restart, logdata)
            if res:
                #end the log

                self.logger.info("Game restart message received. Closing this log file")

                self.GAME_OVER = True
                self.endLogParsing(True)

                return

            #don't want to record stats that happen after round_win (bonustime kills and shit)
            if not self.ROUND_PAUSE:
            #begin round_pause blocking
                #damage dealt
                res = regex(parser_regex.damage_dealt, logdata)
                if (not self._using_livelogs_output and res):
                    #print "Damage dealt"
                    #pprint(res.groups())
                    #('[v3] Kaki', '51', 'STEAM_0:1:35387674', 'Red', '40')
                    sid = regml(res, 3)
                    name = self.escapePlayerString(regml(res, 1))
                    dmg = regml(res, 5)

                    #pg_statupsert(self, table, column, steamid, name, value)
                    self.pg_statupsert(self.STAT_TABLE, "damage_dealt", sid, name, dmg)        
                    
                    self.insertPlayerTeam(sid, regml(res, 4).lower())

                    self.playerLogIndex(sid)
                    
                    return

                #damage taken (if log level is 1 in livelogs) shouldn't get double ups, but have toggling variable just in case
                res = regex(parser_regex.damage_taken, logdata)
                if (not self._using_livelogs_output and res):
                    sid = regml(res, 3)
                    name = self.escapePlayerString(regml(res, 1))
                    dmg = regml(res, 5)

                    self.pg_statupsert(self.STAT_TABLE, "damage_taken", sid, name, dmg)

                    self.insertPlayerTeam(sid, regml(res, 4).lower())
                    self.playerLogIndex(sid)

                    return

                #damage taken and dealt (if appropriate log level is set (damage taken and damage dealt))
                #"Cinderella:wu<5><STEAM_0:1:18947653><Blue>" triggered "damage" against "jmh<19><STEAM_0:1:101867><Red>" (damage "56")
                res = regex(parser_regex.player_damage, logdata)
                if res:
                    a_sid = regml(res, 3)
                    a_name = self.escapePlayerString(regml(res, 1))

                    v_sid = regml(res, 7)
                    v_name = self.escapePlayerString(regml(res, 5))

                    dmg = regml(res, 9)

                    if a_sid == v_sid: #players can deal self damage. if so, don't record damage_dealt for this
                        self.insertPlayerTeam(a_sid, regml(res, 4).lower())

                    else:
                        self.pg_statupsert(self.STAT_TABLE, "damage_dealt", a_sid, a_name, dmg)
                        self.insertPlayerTeam(a_sid, regml(res, 4).lower(), v_sid, regml(res, 8).lower())

                    self.pg_statupsert(self.STAT_TABLE, "damage_taken", v_sid, v_name, dmg)

                    self.playerLogIndex(a_sid, v_sid)

                    self._using_livelogs_output = True

                    return

                #healing done
                #"vsn.RynoCerus<6><STEAM_0:0:23192637><Blue>" triggered "healed" against "Hyperbrole<3><STEAM_0:1:22674758><Blue>" (healing "26")
                res = regex(parser_regex.healing_done, logdata)
                if res:
                    #print "Healing done"
                    #pprint(res.groups())

                    medic_sid = regml(res, 3)
                    medic_name = self.escapePlayerString(regml(res, 1))
                    medic_healing = regml(res, 9)
                    medic_points = round(int(medic_healing) / 600, 2)

                    healt_name = self.escapePlayerString(regml(res, 5))
                    healt_sid = regml(res, 7)
                    
                    self.pg_statupsert(self.STAT_TABLE, "healing_done", medic_sid, medic_name, medic_healing)
                    self.pg_statupsert(self.STAT_TABLE, "points", medic_sid, medic_name, medic_points)
                    self.pg_statupsert(self.STAT_TABLE, "healing_received", healt_sid, healt_name, medic_healing)

                    self.insertPlayerTeam(medic_sid, regml(res, 4).lower(), healt_sid, regml(res, 8).lower())
                    self.playerLogIndex(medic_sid, healt_sid)

                    return

                #item picked up
                #"skae<14><STEAM_0:1:31647857><Red>" picked up item "ammopack_medium"
                res = regex(parser_regex.item_pickup, logdata)
                if res:
                    #print "Item picked up"
                    #pprint(res.groups())

                    sid = regml(res, 3)
                    name = self.escapePlayerString(regml(res, 1))

                    colname = self.selectItemName(regml(res, 5))

                    if not colname:
                        return

                    self.pg_statupsert(self.STAT_TABLE, colname, sid, name, 1) #add 1 to whatever item was picked up


                    return

                #player killed (normal)
                res = regex(parser_regex.player_kill, logdata)
                if res:
                    #print "Player killed (normal kill)"
                    #pprint(res.groups())
                    k_sid = regml(res, 3)
                    k_name = self.escapePlayerString(regml(res, 1))
                    k_pos = regml(res, 10)
                    k_weapon = regml(res, 9)

                    v_sid = regml(res, 7)
                    v_name = self.escapePlayerString(regml(res, 5))
                    v_pos = regml(res, 11)

                    #killer stats
                    self.pg_statupsert(self.STAT_TABLE, "kills", k_sid, k_name, 1) #add kill to killer stat
                    self.pg_statupsert(self.STAT_TABLE, "points", k_sid, k_name, 1) #add point to killer
         
                    #victim stats
                    self.pg_statupsert(self.STAT_TABLE, "deaths", v_sid, v_name, 1) #add death to victim stat

                    #increment event ids and SHIT
                    event_insert_query = "INSERT INTO %s (event_time, event_type, kill_attacker_id, kill_attacker_pos, kill_victim_id, kill_victim_pos) VALUES (E'%s', E'%s', E'%s', E'%s', E'%s', E'%s')" % (self.EVENT_TABLE, 
                                                            event_time, "kill", k_sid, k_pos, v_sid, v_pos) #creates a new, unique eventid with details of the event
                    self.executeQuery(event_insert_query)

                    self.insertPlayerTeam(k_sid, regml(res, 4).lower(), v_sid, regml(res, 8).lower())
                    self.playerLogIndex(k_sid, v_sid)
                    
                    return

                #player killed (special kill) 
                #"Liquid'Time<41><STEAM_0:1:19238234><Blue>" killed "[v3] Roight<53><STEAM_0:0:8283620><Red>" with "knife" (customkill "backstab") (attacker_position "-1085 99 240") (victim_position "-1113 51 240")
                res = regex(parser_regex.player_kill_special, logdata)
                if res:
                    #print "Player killed (customkill)"
                    #pprint(res.groups())
            
                    ck_type = regml(res, 10)

                    if (ck_type == "feign_death"):
                        return
                
                    event_type = "kill_custom"
                
                    k_sid = regml(res, 3)
                    k_name = self.escapePlayerString(regml(res, 1))
                    k_pos = regml(res, 11)
                    k_weapon = regml(res, 9)

                    v_sid = regml(res, 7)
                    v_name = self.escapePlayerString(regml(res, 5))
                    v_pos = regml(res, 12)

                    self.pg_statupsert(self.STAT_TABLE, "kills", k_sid, k_name, 1)

                    if (ck_type == "backstab"):
                        self.pg_statupsert(self.STAT_TABLE, "backstabs", k_sid, k_name, 1)
                        self.pg_statupsert(self.STAT_TABLE, "points", k_sid, k_name, 2)

                        event_type = "kill_custom_backstab"
                    elif (ck_type == "headshot"):
                        self.pg_statupsert(self.STAT_TABLE, "headshots", k_sid, k_name, 1)
                        self.pg_statupsert(self.STAT_TABLE, "points", k_sid, k_name, 1.5)

                        event_type = "kill_custom_headshot"
                    else:
                        #print "ERROR: UNKNOWN CUSTOM KILL TYPE \"%s\"" % ck_type
                        
                        return

                    event_insert_query = "INSERT INTO %s (event_time, event_type, kill_attacker_id, kill_attacker_pos, kill_victim_id, kill_victim_pos) VALUES (E'%s', '%s', E'%s', E'%s', E'%s', E'%s')" % (self.EVENT_TABLE,
                                                            event_time, event_type, k_sid, k_pos, v_sid, v_pos)
                    self.executeQuery(event_insert_query)

                    return
                
                #player assist
                #"Iyvn<40><STEAM_0:1:41931908><Blue>" triggered "kill assist" against "[v3] Kaki<51><STEAM_0:1:35387674><Red>" (assister_position "-905 -705 187") (attacker_position "-1246 -478 237") (victim_position "-1221 -53 283")
                res = regex(parser_regex.player_assist, logdata)
                if res:
                    #print "Player assisted in kill"
                    #pprint(res.groups())
                    a_sid = regml(res, 3)
                    a_name = self.escapePlayerString(regml(res, 1))
                    a_pos = regml(res, 9)

                    #increment stats!
                    self.pg_statupsert(self.STAT_TABLE, "assists", a_sid, a_name, 1)
                    self.pg_statupsert(self.STAT_TABLE, "points", a_sid, a_name, 0.5)

                    #kill assist ALWAYS (99.9999999999999%) comes after a kill, so we use the previous event id from inserting the kill into the event table. might need to change later
                    assist_update_query = "UPDATE %s SET kill_assister_id = E'%s', kill_assister_pos = E'%s' WHERE eventid = (SELECT eventid FROM %s WHERE event_type = 'kill' ORDER BY eventid DESC LIMIT 1)" % (self.EVENT_TABLE, 
                                                                a_sid, a_pos, self.EVENT_TABLE)
                    self.executeQuery(assist_update_query)

                    self.insertPlayerTeam(a_sid, regml(res, 4).lower())
                    self.playerLogIndex(a_sid)

                    return

                #medic death ubercharge = 0 or 1, healing = amount healed in that life. kill message comes directly after
                #"%s<%i><%s><%s>" triggered "medic_death" against "%s<%i><%s><%s>" (healing "%d") (ubercharge "%s")
                res = regex(parser_regex.medic_death, logdata)
                if res:
                    #print "Medic death"
                    #pprint(res.groups())
                    m_sid = regml(res, 7)
                    m_name = self.escapePlayerString(regml(res, 5))
                    m_healing = regml(res, 9)
                    m_uberlost = regml(res, 10)

                    self.pg_statupsert(self.STAT_TABLE, "ubers_lost", m_sid, m_name, m_uberlost) #may increment, or may do nothing (uberlost = 0 or 1)
            
                    #put medic_death info into event table
                    event_insert_query = "INSERT INTO %s (event_time, event_type, medic_steamid, medic_uber_lost, medic_healing) VALUES (E'%s', '%s', E'%s', '%s', '%s')" % (self.EVENT_TABLE, 
                                                           event_time, "medic_death", m_sid, m_uberlost, m_healing)
                    self.executeQuery(event_insert_query)

                    return

                #ubercharge used
                res = regex(parser_regex.uber_used, logdata)
                if res:
                    #print "Ubercharge used"
                    #pprint(res.groups())
                    m_sid = regml(res, 3)
                    m_name = self.escapePlayerString(regml(res, 1))

                    self.pg_statupsert(self.STAT_TABLE, "ubers_used", m_sid, m_name, 1)

                    event_insert_query = "INSERT INTO %s (event_time, event_type, medic_steamid, medic_uber_used) VALUES (E'%s', '%s', E'%s', '%s')" % (self.EVENT_TABLE, 
                                                            event_time, "uber_used", m_sid, 1)
                    self.executeQuery(event_insert_query)

                    return

                #domination
                res = regex(parser_regex.player_dominated, logdata)
                if res:
                    #print "Player dominated"
                    #pprint(res.groups())

                    p_sid = regml(res, 3)
                    p_name = self.escapePlayerString(regml(res, 1))

                    v_sid = regml(res, 7)
                    v_name = self.escapePlayerString(regml(res, 5))

                    self.pg_statupsert(self.STAT_TABLE, "dominations", p_sid, p_name, 1)
                    self.pg_statupsert(self.STAT_TABLE, "times_dominated", v_sid, v_name, 1)


                    return

                #revenge
                res = regex(parser_regex.player_revenge, logdata)
                if res:
                    #print "Player got revenge"
                    #pprint(res.groups())

                    p_sid = regml(res, 3)
                    p_name = self.escapePlayerString(regml(res, 1))

                    self.pg_statupsert(self.STAT_TABLE, "revenges", p_sid, p_name, 1)

                    return
                
                #suicide
                #"Hypnos<20><STEAM_0:0:24915059><Red>" committed suicide with "world" (customkill "train") (attacker_position "568 397 -511")
                res = regex(parser_regex.player_death_custom, logdata)
                if res:
                    #print "Player committed suicide"
                    #pprint(res.groups())

                    p_sid = regml(res, 3)
                    p_name = self.escapePlayerString(regml(res, 1))

                    self.pg_statupsert(self.STAT_TABLE, "suicides", p_sid, p_name, 1)
                    self.pg_statupsert(self.STAT_TABLE, "deaths", p_sid, p_name, 1)

                    return

                # 11/13/2012 - 23:03:29: "crixus of gaul<3><STEAM_0:1:10325827><Blue>" committed suicide with "tf_projectile_rocket" (attacker_position "-1233 5907 -385")
                res = regex(parser_regex.player_death, logdata)
                if res:
                    #print "Player committed suicide"
                    #pprint(res.groups())
                    
                    p_sid = regml(res, 3)
                    p_name = self.escapePlayerString(regml(res, 1))
                    
                    self.pg_statupsert(self.STAT_TABLE, "suicides", p_sid, p_name, 1)
                    self.pg_statupsert(self.STAT_TABLE, "deaths", p_sid, p_name, 1)
                    
                    return
                    
                #engi building destruction
                #"dcup<109><STEAM_0:0:15236776><Red>" triggered "killedobject" (object "OBJ_SENTRYGUN") (weapon "tf_projectile_pipe") (objectowner "NsS. oLiVz<101><STEAM_0:1:15674014><Blue>") (attacker_position "551 2559 216")
                res = regex(parser_regex.building_destroyed, logdata)
                if res:
                    #print "Player destroyed engineer building"
                    #pprint(res.groups())

                    p_sid = regml(res, 3)
                    p_name = self.escapePlayerString(regml(res, 1))

                    self.pg_statupsert(self.STAT_TABLE, "buildings_destroyed", p_sid, p_name, 1)
                    self.pg_statupsert(self.STAT_TABLE, "points", p_sid, p_name, 1)

                    return
            #end round_pause blocking
            
            #chat
            #"Console<0><Console><Console>" say "blah"
            res = regex(parser_regex.chat_message, logdata)
            if res:
                #print "Chat was said"
                #pprint(res.groups())

                c_sid = regml(res, 3)
                if c_sid is "Console":
                    c_sid = "STEAM_0:0:0"

                c_name = self.escapePlayerString(regml(res, 1))
                c_team = regml(res, 4)

                chat_type = regml(res, 5)
                chat_message = self.escapePlayerString(regml(res, 6))

                event_insert_query = "INSERT INTO %s (event_time, event_type) VALUES (E'%s', '%s')" % (self.EVENT_TABLE, event_time, "chat")
                self.executeQuery(event_insert_query)

                if not self.db.closed:
                    curs = self.db.cursor()
                    try:
                        #now we need to get the event ID and put it into chat!
                        
                        eventid_query = "SELECT eventid FROM %s WHERE event_type = 'chat' ORDER BY eventid DESC LIMIT 1" % self.EVENT_TABLE
                        curs.execute(eventid_query)
                        eventid = curs.fetchone()[0]

                        chat_insert_query = "INSERT INTO %s (eventid, steamid, name, team, chat_type, chat_message) VALUES ('%s', E'%s', E'%s', '%s', '%s', E'%s')" % (self.CHAT_TABLE, 
                                                                eventid, c_sid, c_name, c_team, chat_type, chat_message)

                        self.executeQuery(chat_insert_query, curs=curs) #execute query will perform the insert query, commit, and close the cursor

                    except Exception, e:
                        self.logger.exception("Exception trying to get chat eventid")

                return        
            
            #point capture
            #/Team "(Blue|Red)" triggered "pointcaptured" \x28cp "(\d+)"\x29 \x28cpname "(.+)"\x29 \x28numcappers "(\d+)".+/
            #Team "Red" triggered "pointcaptured" (cp "0") (cpname "#koth_viaduct_cap") (numcappers "5") (player1 "[v3] Faithless<47><STEAM_0:0:52150090><Red>") (position1 "-1370 59 229") (player2 "[v3] Chrome<48><STEAM_0:1:41365809><Red>") (position2 "-1539 87 231") (player3 "[v3] Jak<49><STEAM_0:0:18518582><Red>") (position3 "-1659 150 224") (player4 "[v3] Kaki<51><STEAM_0:1:35387674><Red>") (position4 "-1685 146 224") (player5 "[v3] taintedromance<52><STEAM_0:0:41933053><Red>") (position5 "-1418 182 236")
            res = regex(parser_regex.point_capture, logdata)
            if res:
                #print "Point captured"
                #pprint(res.groups())
                #this is going to be tricky
                cap_team = regml(res, 1)
                cap_name = self.escapePlayerString(regml(res, 3))
                num_cappers = regml(res, 4)
                
                event_insert_query = "INSERT INTO %s (event_time, event_type, capture_name, capture_team, capture_num_cappers) VALUES (E'%s', '%s', E'%s', '%s', '%s')" % (self.EVENT_TABLE,
                                                        event_time, "point_capture", cap_name, cap_team, num_cappers)

                self.executeQuery(event_insert_query)

                #INPUT: (player2 "[v3] Chrome<48><STEAM_0:1:41365809><Red>")
                capper_re = re.compile(r'\x28player(\d) "(.*?)<(\d+)><(.*?)><(Red|Blue)>"')
                #OUTPUT: ('2', '[v3] Chrome', '48', 'STEAM_0:1:41365809', 'Red')            

                for capper in capper_re.finditer(logdata):
                    #print "Capper:"
                    #pprint(capper.groups())

                    c_sid = regml(capper, 4)
                    c_name = self.escapePlayerString(regml(capper, 2))

                    self.pg_statupsert(self.STAT_TABLE, "captures", c_sid, c_name, 1)
                    self.pg_statupsert(self.STAT_TABLE, "points", c_sid, c_name, 2)

                return

            #capture block
            #"pvtx<103><STEAM_0:1:7540588><Red>" triggered "captureblocked" (cp "1") (cpname "Control Point B") (position "-2143 2284 156")
            res = regex(parser_regex.capture_blocked, logdata)
            if res:
                #print "Capture blocked"
                #pprint(res.groups())

                cb_sid = regml(res, 3)
                cb_name = self.escapePlayerString(regml(res, 1))

                self.pg_statupsert(self.STAT_TABLE, "captures_blocked", cb_sid, cb_name, 1)
                self.pg_statupsert(self.STAT_TABLE, "points", cb_sid, cb_name, 1)

                cap_name = self.escapePlayerString(regml(res, 6))
                cap_block_team = regml(res, 4)

                #re-use the capture event columns, but this time capture_blocked is 1 instead of NULL, so we can distinguish
                event_insert_query = "INSERT INTO %s (event_time, event_type, capture_name, capture_team, capture_blocked) VALUES (E'%s', '%s', E'%s', '%s', '%s')" % (self.EVENT_TABLE,
                                                        event_time, "point_capture_block", cap_name, cap_block_team, 1)

                self.executeQuery(event_insert_query)

                return
                
            #current score (shown after round win/round length)
            #L 10/21/2012 - 01:23:48: World triggered "Round_Win" (winner "Blue")
            #L 10/21/2012 - 01:23:48: World triggered "Round_Length" (seconds "88.26")
            #L 10/21/2012 - 01:23:48: Team "Red" current score "0" with "6" players
            #L 10/21/2012 - 01:23:48: Team "Blue" current score "4" with "6" players
            #Team "Blue" current score "3" with "4" players
            res = regex(parser_regex.team_score, logdata)
            if res:
                #print "Current scores"
                #pprint(res.groups())

                team = regml(res, 1)
                t_score = regml(res, 2)
                #t_players = regml(res, 3)

                #use previous round_win event id. Round_Win WILL ****ALWAYS**** trigger before this event (presuming we don't get gayed and lose packets along the way)
                event_update_query = "UPDATE %s SET round_%s_score = '%s' WHERE eventid = (SELECT eventid FROM %s WHERE event_type = 'round_end' ORDER BY eventid DESC LIMIT 1)" % (self.EVENT_TABLE, 
                                                        team.lower(), t_score, self.EVENT_TABLE)

                self.executeQuery(event_update_query)
                
                self.ROUND_PAUSE = True

                return

            #game over
            res = regex(parser_regex.game_over, logdata)
            if res:
                #print "Game over"
                #pprint(res.groups())
            
                go_reason = regml(res, 1)

                event_insert_query = "INSERT INTO %s (event_time, event_type, game_over_reason) VALUES (E'%s', '%s', E'%s')" % (self.EVENT_TABLE, event_time, "game_over", go_reason)
                self.executeQuery(event_insert_query)
                
                return

            #final scores always comes after game_over
            res = regex(parser_regex.final_team_score, logdata)
            if res:
                #print "Final scores"
                #pprint(res.groups())

                fs_team = regml(res, 1)
                fs_score = regml(res, 2)
                
                final_score_query = "UPDATE %s SET round_%s_score = '%s' WHERE event_type = 'game_over'" % (self.EVENT_TABLE, fs_team.lower(), fs_score)
                self.executeQuery(final_score_query)

                if (fs_team == "Blue"): #red's final score is shown before blue's
                    self.GAME_OVER = True
                    self.endLogParsing(True)
                
                return

            #rcon command
            res = regex(parser_regex.rcon_command, logdata)
            if res:
                #print "Someone issued rcon command"
                #pprint(res.groups())

                return


            #disconnect RL 10/07/2012 - 01:13:44: "triple h<162><STEAM_0:1:33713004><Red>" disconnected (reason " #tf2pug")
            res = regex(parser_regex.player_disconnect, logdata)
            if res:
                #print "Player disconnected"
                #pprint(res.groups())
                
                return
            
            #connect RL 10/07/2012 - 22:45:11: "GU | wm<3><STEAM_0:1:7175436><>" connected, address "124.168.51.7:27005"
            res = regex(parser_regex.player_connect, logdata)
            if res:
                #print "Player connected"
                #pprint(res.groups())

                return

            #validated "hipsterhipster<4><STEAM_0:1:22674758><>" STEAM USERID validated
            res = regex(parser_regex.player_validated, logdata)
            if res:
                #print "Player validated"
                #pprint(res.groups())

                return
            
            #class change    
            res = regex(parser_regex.player_class_change, logdata)
            if res:
                #print "Player changed class"
                #pprint(res.groups())

                return

            #round win
            res = regex(parser_regex.round_win, logdata)
            if res:
                #print "Round won"
                #pprint(res.groups())

                event_insert_query = "INSERT INTO %s (event_time, event_type) VALUES (E'%s', '%s')" % (self.EVENT_TABLE, event_time, "round_end")

                self.executeQuery(event_insert_query)

                return

            #overtime
            res = regex(parser_regex.round_overtime, logdata)
            if res:
                #print "Overtime"
                #pprint(res.groups())

                event_insert_query = "INSERT INTO %s (event_time, event_type) VALUES (E'%s', '%s')" % (self.EVENT_TABLE, event_time, "round_overtime")

                self.executeQuery(event_insert_query)

                return

            #round length
            #World triggered "Round_Length" (seconds "402.58")
            #World triggered "Round_Length" \x28seconds "(\d+\.\d+)\x29
            #World triggered "Round_length" \x28seconds "(\d+)\.(\d+)"\x29
            res = regex(parser_regex.round_length, logdata)
            if res:
                #print "Round length"
                #pprint(res.groups())
        
                r_length = "%s.%s" % (regml(res, 1), regml(res, 2))

                event_update_query = "UPDATE %s SET round_length = '%s' WHERE eventid = (SELECT eventid FROM %s WHERE event_type = 'round_end' ORDER BY eventid DESC LIMIT 1)" % (self.EVENT_TABLE, r_length, self.EVENT_TABLE)

                self.executeQuery(event_update_query)

                return
                
            #round start
            res = regex(parser_regex.round_start, logdata)
            if res:
                #print "Round start"
                #pprint(res.groups())

                event_insert_query = "INSERT INTO %s (event_time, event_type) VALUES (E'%s', '%s')" % (self.EVENT_TABLE, event_time, "round_start")

                self.executeQuery(event_insert_query)

                self.ROUND_PAUSE = False
                
                return
                
            #setup end UNUSED
            """res = regex(parser_regex.round_setup_end, logdata)
            if res:
                #print "Round Setup End"
                #pprint(res.groups())

                return
            """

            #mini round win
            res = regex(parser_regex.mini_round_win, logdata)
            if res:
                #print "Mini round win"
                #pprint(res.groups())

                return

            #mini round length
            res = regex(parser_regex.mini_round_length, logdata)
            if res:
                #print "Mini round length"
                #pprint(res.groups())

                return

            res = regex(parser_regex.map_change, logdata)
            if res:
                self.logger.info("Map changed to %s. Ending this log", regml(res, 1))

                self.GAME_OVER = True
                self.endLogParsing(True)

                return

            if not self.ROUND_PAUSE:
                self.logger.info("Reached end of regex checks with no match. Round pause: %d. Log data: %s", self.ROUND_PAUSE, logdata)

        except Exception, e:
            self.logger.exception("Exception parsing log data: %s", logdata)

    def regex(self, compiled_regex, string): #helper function for performing regular expression checks. avoids having to compile and match in-function 1000 times
        #preg = re.compile(expression, re.IGNORECASE | re.MULTILINE)
        
        match = compiled_regex.search(string)
        #print expression + " match?: "
        #print match
        return match

    def regml(self, retuple, index): #get index of re group tuple
        return retuple.group(index)

    def selectItemName(self, item_name):
        if item_name in self.ITEM_DICT:
            return self.ITEM_DICT[item_name]

    def pg_statupsert(self, table, column, steamid, name, value):
        #takes all the data that would usually go into an upsert, allows for cleaner code in the regex parsing
        insert_query = "INSERT INTO %s (steamid, name, %s) VALUES (E'%s', E'%s', E'%s')" % (self.STAT_TABLE, column, steamid, name, value)
        update_query = "UPDATE %s SET %s = COALESCE(%s, 0) + %s WHERE steamid = E'%s'" % (self.STAT_TABLE, column, column, value, steamid)
        try:
            if not self.db.closed:
                curs = self.db.cursor()
                
                try:
                    curs.execute("SELECT pgsql_upsert(%s, %s)", (insert_query, update_query,))
                    self.db.commit()
                except psycopg2.DataError, e:
                    self.logger.exception("DB DATA ERROR INSERTING DATA %s", query)
                    
                    self.db.rollback()
                except Exception, e:
                    self.logger.exception("DB ERROR")
                    
                    self.db.rollback()
                finally:
                    if not self.db.closed: #the cursor will auto close if the db closes for whatever reason
                        curs.close()

            else:
                if not self.RECONNECTING_TO_DATABASE:
                    self.reconnectToDatabase()

                self.addToQueryQueue("upsert", insert_query, update_query)
        except:
            self.logger.exception("Exception occurred rolling back the connection")

    def escapePlayerString(self, unescaped_string):
        escaped_string = unescaped_string.replace("'", "''").replace("\\", "\\\\")
        escaped_string = stripHTMLTags(escaped_string)

        return escaped_string

    #this method can take up to two players and insert their teams into the database
    def insertPlayerTeam(self, a_sid, a_team, b_sid = None, b_team = None):
        team_insert_list = []

        if a_sid not in self.PLAYER_TEAMS:
            self.PLAYER_TEAMS[a_sid] = a_team
            
            team_insert_list.append((self.STAT_TABLE, a_sid, a_team))
        
        if b_sid and b_team:
            if b_sid not in self.PLAYER_TEAMS:
                self.PLAYER_TEAMS[b_sid] = b_team
            
                team_insert_list.append((self.STAT_TABLE, b_sid, b_team))
        
        if len(team_insert_list) > 0:
            if not self.db.closed:
                try:
                    curs = self.db.cursor()
                    #team_insert_query = ';'.join(("UPDATE %s SET team = E'%s' WHERE steamid = E'%s'" % team_tuple) for team_tuple in team_insert_list)
                    #self.executeQuery(team_insert_query)
                    for team_tuple in team_insert_list:
                        insert_query = "INSERT INTO %s (steamid, team) VALUES (E'%s', E'%s')" % team_tuple
                        update_query = "UPDATE %s SET team = E'%s' WHERE steamid = E'%s'" % (self.STAT_TABLE, team_tuple[2], team_tuple[1])

                        curs.execute("SELECT pgsql_upsert(%s, %s)", (insert_query, update_query,))

                    self.db.commit()

                except:
                    self.logger.exception("Error during team insertion")
                    self.db.rollback()

                finally:
                    curs.close()

            
            #team_insert_args = ','.join(curs.mogrify("(%s, %s)", team_tuple) for team_tuple in team_insert_list)
            #team_insert_query = "INSERT INTO %s (steamid, team) VALUES %s" % (self.STAT_TABLE, team_insert_args)
            
            #self.executeQuery(team_insert_query, curs)
    
    def playerLogIndex(self, a_sid, b_sid = None):
        insert_list = []

        if a_sid not in self._player_logs:
            self._player_logs[a_sid] = True

            insert_list.append(a_sid)

        if b_sid and b_sid not in self._player_logs:
            self._player_logs[b_sid] = True

            insert_list.append(b_sid)

        if len(insert_list) > 0:
            if not self.db.closed:
                curs = self.db.cursor()

                insert_args = ','.join(curs.mogrify("(%s, %s)", insert_tuple) for insert_tuple in insert_list)
                insert_query = "INSERT INTO livelogs_player_logs (steamid, log_ident) VALUES %s" % (insert_args)

                self.executeQuery(insert_query, curs)


    def executeQuery(self, query, curs=None):
        try:
            if not self.db.closed:
                if not curs:
                    curs = self.db.cursor()
                    
                try:
                    curs.execute(query)
                    self.db.commit()
                except psycopg2.DataError, e:
                    self.logger.exception("DB DATA ERROR INSERTING DATA %s", query)
                    
                    self.db.rollback()
                except Exception, e:
                    self.logger.exception("DB ERROR")
                    
                    self.db.rollback()
                finally:
                    if not self.db.closed: #the cursor will auto close if the db closes for whatever reason
                        curs.close()

            else:
                if not self.RECONNECTING_TO_DATABASE:
                    self.reconnectToDatabase()

                self.addToQueryQueue("insert", query)
        except:
            self.logger.exception("Exception occurred rolling back the connection")

    def endLogParsing(self, game_over=False):
        if not self.LOG_PARSING_ENDED:
            self.logger.info("Ending log parsing")
            self.LOG_PARSING_ENDED = True
            
            if not self.HAD_ERROR:
                #sets live to false, and merges the stat table with the master stat table
                live_end_query = "UPDATE livelogs_servers SET live = false WHERE log_ident = E'%s'; SELECT merge_stat_table('%s')" % (self.UNIQUE_IDENT, self.STAT_TABLE)
                self.executeQuery(live_end_query)
                
                #begin ending timer
                if ((self.closeListenerCallback != None) and (game_over)):
                    self.closeListenerCallback(game_over)

            if self.db:
                if not self.db.closed:
                    self.db.close()
            
            if self.LOG_FILE_HANDLE:
                if not self.LOG_FILE_HANDLE.closed:
                    self.LOG_FILE_HANDLE.close()

    def reconnectToDatabase(self):
        if self.db.closed and not self.RECONNECTING_TO_DATABASE:
            self._processing_queue = False
            self.RECONNECTING_TO_DATABASE = True

            self.reconnectThread = threading.Thread(target = self._databaseReconnect)
            self.reconnectThread.daemon = True

            self.reconnectThread.start()

    def _databaseReconnect(self):
        loops = 0

        new_connection = None
        time.sleep(5) #wait 5 seconds before starting loop, so the database has time to close properly if it was shut down

        while self.db.closed:
            #loop X times while the DB is closed
            self.logger.info("Attempting to reconnect to the database...")
            if loops < 10:
                try:
                    new_connection = psycopg2.connect(self._db_dsn)

                except:
                    self.logger.exception("Exception trying to reconnect to database")

                finally:
                    if new_connection and not new_connection.closed:
                        #we have the connection! now we need to assign it
                        self.logger.info("Successfully reconnected to the database")
                        self.db = new_connection

                        self.RECONNECTING_TO_DATABASE = False

                        #process the queue... this has to block. not going to worry about it for now. just need to get this fix out
                        #TODO: process the queue!
                        self._query_queue = [] #just empty the queue for now

                        break #break out of the while loop, terminating the thread

                    else:
                        #wait 10 seconds before trying to connect again
                        loops += 1
                        time.sleep(10)
            else:
                break

    def addToQueryQueue(self, query_type, insert_query, update_query=None):
        #adds the query to the query queue
        if not self._processing_queue:

            self._query_queue.append(queryQueueDataObject(query_type, insert_query, update_query))

    def processQueryQueue(self):
        #called once the parser has reconnected to the database. will process the query queue, adding all data to the appropriate tables
        self._processing_queue = True

        pass

    def __del__(self):
        if self.LOG_FILE_HANDLE:
            if not self.LOG_FILE_HANDLE.closed:
                self.LOG_FILE_HANDLE.close()
        
        if self.db:    
            if not self.db.closed:
                self.endLogParsing()
                #self.db.close()

class queryQueueDataObject(object):
    #this class is just a data structure to hold query information for the query queue
    def __init__(self, query_type, insert_query, update_query=None):
        self.query_type = query_type
        self.insert_query = insert_query
        self.update_query = update_query

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