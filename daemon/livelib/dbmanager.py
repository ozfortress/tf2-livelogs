import threading
import logging
import time
import random

from pprint import pprint

try:
    import psycopg2
except ImportError:
    print """You are missing psycopg2.
    Install using `pip install psycopg2` or visit http://initd.org/psycopg/
    """
    quit()

log_message_format = logging.Formatter(fmt="[(%(levelname)s) %(process)s %(asctime)s %(module)s:%(name)s:%(lineno)s] %(message)s", datefmt="%H:%M:%S")

log_file_handler = logging.handlers.TimedRotatingFileHandler("websocket-server-dbmanager.log", when="midnight")
log_file_handler.setFormatter(log_message_format)
log_file_handler.setLevel(logging.DEBUG)


stat_columns = (
            "steamid",
            "team",
            "class",
            "kills",
            "deaths",
            "assists",
            "points",
            "healing_done",
            "healing_received",
            "overhealing_done",
            "overhealing_received",
            "ubers_used",
            "ubers_lost",
            "headshots",
            "airshots",
            "damage_dealt",
            "damage_taken",
            "captures"
        )


team_stat_columns = (
                "team_kills",
                "team_deaths",
                "team_healing_done",
                "team_overhealing_done",
                "team_damage_dealt",
            )

# from google colour chart http://there4development.com/blog/2012/05/02/google-chart-color-list/
heal_pie_colours = ( 
                "#3366CC", "#DC3912", "#FF9900",
                "#109618", "#990099", "#0099C6", 
                "#DD4477", "#B82E2E", "#316395",
                "#994499", "#22AA99", "#AAAA11",
                "#6633CC", "#E67300", "#329262",
                "#5574A6", "#3B3EAC"
            )


DB_STAT_TABLE = "livelogs_player_stats"
DB_CHAT_TABLE = "livelogs_game_chat"
DB_PLAYER_TABLE = "livelogs_player_details"
DB_EVENT_TABLE = "livelogs_game_events"


"""
The database manager class holds copies of a log's data. It provides functions to calculate the difference between
currently stored data and new data (delta compression) which will be sent to the clients, along with time and chat data
"""
class dbManager(object):
    def __init__(self, db, log_id, db_lock, update_rate, start_time):
        #end_callback is the function to be called when the log is no longer live
        
        self.log = logging.getLogger(log_id)
        self.log.setLevel(logging.INFO)
        self.log.addHandler(log_file_handler)

        self.db = db
        self.database_lock = db_lock
        self.update_rate = update_rate
        self._unique_ident = log_id
        
        self._stat_table = {} #a dict containing stat data
        self._stat_difference_table = {} #a dict containing the difference between stored and retrieved stat data

        self._chat_table = {} #a dict containing recent chat messages

        self._score_table = {} #a dict containing the most recent scores
        self._score_difference_table = {} #a dict containing the difference in score updates

        self._start_time = int(round(time.mktime(time.strptime(start_time, "%Y-%m-%d %H:%M:%S")))) #a variable containing the log start time in seconds since epoch
        
        self._team_stat_table = {} #dict containing team stats
        self._team_stat_difference_table = {} #dict containing team stat differences

        self._name_table = {} #a dict containing player names wrt to steamids

        self._player_colours = {} # a dict mapping hex colours to cids, such that we have constant colours in heal spreads

        self._log_status_check = False
        self._database_busy = False
        self.ended = False
        
        self._chat_event_id = 0 #maintain a copy of the last retreived chat event id

        self._new_stat_update = False
        self._new_team_stat_update = False
        self._new_chat_update = False
        self._new_score_update = False

        #construct some of the queries here, because they will remain constant throughout the log

        self._default_chat_query = "SELECT MAX(id) FROM %s WHERE log_ident = '%s'" % (DB_CHAT_TABLE, self._unique_ident) #need to get the most recent id for first update, to prevent chat duplicates

        self._stat_query = self.construct_stat_query()

        self._score_query = "SELECT COALESCE(round_red_score, 0), COALESCE(round_blue_score, 0) FROM %s WHERE (round_red_score IS NOT NULL AND round_blue_score IS NOT NULL) AND log_ident = '%s' ORDER BY eventid DESC LIMIT 1" % (DB_EVENT_TABLE, self._unique_ident)

        self._team_stat_query = self.construct_team_stat_query()

        self._name_query = "SELECT name, steamid FROM %s WHERE log_ident = '%s'" % (DB_PLAYER_TABLE, self._unique_ident)

        self.log.info("DB Manager for log ident %s established", log_id)
    
    def stat_idx_to_name(self, index, teams=False):
        #converts an index in the stat tuple to a name for use in dictionary keys
        if teams:
            return team_stat_columns[index]
        else:
            return stat_columns[index]
    
    def stat_tuple_to_dict(self, stat_tuple):
        #takes a stat tuple and converts it to a simple dictionary
        
        stat_dict = {}
        
        for idx, val in enumerate(stat_tuple):
            col = self.stat_idx_to_name(idx)
            if col == "steamid":
                stat_dict[col] = val

            else:    
                if val > 0: #ignore zero values when sending updates
                    if col == "points": #catch the points, which are auto converted Decimal, and aren't handled by tornado's json encoder
                        stat_dict[col] = float(val)
                    else:
                        stat_dict[col] = val
                    
        return stat_dict

    def merge_stat_list(self, player_list):
        #takes a list of dicts with multiple dicts per player and combines them on steamid
        merged_dict = {}

        for player_data in player_list:
            cid = player_data["steamid"] # get the steamid out

            # create a new entry in the merged dict for this cid if not present
            if cid not in merged_dict:
                merged_dict[cid] = {}
        
            merged_stat = merged_dict[cid] #combined stats for this player

            for statcol in player_data: #each cid in the stat_dict has a dict of stats, with table columns and values
                if statcol == "steamid":
                    continue #skip over the steamid key

                if statcol not in merged_stat:
                    #if the key doesn't exist in the merged dict, add it and assign the current value
                    merged_stat[statcol] = player_data[statcol]

                else:
                    #if the key DOES exist in the merged dict, we have to either add the value or append a string depending on the column
                    if statcol == "class":
                        merged_stat[statcol] = "%s,%s" % (merged_stat[statcol], player_data[statcol])
                        #print "merged class: %s" % merged_stat[statcol]

                    elif statcol == "team":
                        if player_data[statcol] is not None:
                            merged_stat[statcol] = player_data[statcol]
                    else:
                        #just add the values together
                        merged_stat[statcol] += player_data[statcol]

        self.add_player_names(merged_dict) #add names here so that we don't have to worry about doing it elsewhere
        
        #pprint(merged_dict)

        return merged_dict
    
    def team_stat_tuple_to_dict(self, stat_tuple):
        #converts a team stat tuple to a dict
        stat_dict = {}

        for idx, val in enumerate(stat_tuple):
            if val > 0: #ignore 0 values
                col = self.stat_idx_to_name(idx, teams = True)

                stat_dict[col] = int(val)

        return stat_dict

    def full_update(self):
        #constructs and returns a dictionary for a complete update to the client
        update_dict = {}

        if self._stat_table:
            update_dict["stat"] = self._stat_table

            tmp = self.get_heal_spread()
            if tmp:
                update_dict["heal_spread"] = tmp

        if self._score_table:
            update_dict["score"] = self._score_table

        if self._team_stat_table:
            update_dict["team_stat"] = self._team_stat_table

        update_dict["gametime"] = self.calc_game_time()

        return update_dict
    
    def compressed_update(self):
        #returns a dictionary for a delta compressed update to the client
        update_dict = {}

        if self._stat_difference_table and self._new_stat_update:
            self.log.debug("Have stat update diff in compressedUpdate")
            update_dict["stat"] = self._stat_difference_table

            # stats have been changed, most likely heals have been updated. send
            # a heal spread update too
            tmp = self.get_heal_spread()
            if tmp:
                update_dict["heal_spread"] = tmp

            self._new_stat_update = False

        if self._chat_table and self._new_chat_update:
            self.log.debug("Have chat update dict in compressedUpdate")
            update_dict["chat"] = self._chat_table
            self._chat_table = None #clear the chat table, so it cannot be duplicated on next send if update fails

            self._new_chat_update = False

        if self._score_difference_table and self._new_score_update:
            self.log.debug("Have score update dict in compressedUpdate")
            update_dict["score"] = self._score_difference_table

            self._score_difference_table = None #clear score table to prevent duplicates
            self._new_score_update = False

        if self._team_stat_difference_table and self._new_team_stat_update:
            self.log.debug("Have team stat update in compressedUpdate")

            update_dict["team_stat"] = self._team_stat_difference_table

            self._new_team_stat_update = False

        update_dict["gametime"] = self.calc_game_time()

        return update_dict
    
    def calc_game_time(self):
        return int(round(time.time())) - self._start_time

    def calc_table_delta(self, old_table=None, new_table=None):
        """
        Calculates the delta update of two table dicts

        This means that we only want the difference between keys present in the old AND new tables, we don't care if a key is present in the old but not new.
        Keys present in the new table are included in the delta update, because they are clearly an update if they weren't previously present

        """
        
        diff_dict = {}

        if not old_table or not new_table:
            return diff_dict
        
        for key in new_table:
            if key in old_table:
                #find the difference
                if isinstance(old_table[key], dict) and isinstance(new_table[key], dict): #keys are dicts, so we should do this recursively
                    tmp = self.calc_table_delta(old_table = old_table[key], new_table = new_table[key])

                    if tmp:
                        diff_dict[key] = tmp
                
                else:
                    #special case for certain stat dict keys
                    #if the key is "team" and this is a team stat dict, we want to keep the team the same
                    if key == "class":
                        if new_table[key] != old_table[key]:
                            diff_dict[key] = new_table[key]

                    elif key == "team":
                        diff_dict[key] = new_table[key]

                    elif key == "name":
                        if new_table[key] != old_table[key]:
                            diff_dict[key] = new_table[key]

                    else:
                        #we get the difference by subtracting the old from the new
                        diff = new_table[key] - old_table[key]

                        if diff > 0: #ignore 0 values
                            diff_dict[key] = diff
                
            else: #key is in new table, but not old, so it's new and doesnt have a difference to be found
                diff_dict[key] = new_table[key]
                
        return diff_dict
    
    def combine_update_table(self, table_a, table_b):
        #this will add two dictionaries together in the case that two updates occur before data is sent
        update_dict = {}

        for key in table_a:
            if key in table_b:
                #table[key] can be another dict in the case of stat updates, because there's dicts with steamids, and then corresponding stats
                if isinstance(table_a[key], dict) and isinstance(table_b[key], dict): #it's a stat update with key == steamid
                    update_dict[key] = self.combine_update_table(table_a[key], table_b[key]) #recursively combine the lower levels

                else:
                    if key == "class":
                        if table_a[key] != table_b[key]:
                            #whichever key has the longest team string will be the most recent one, because it has the most classes in it

                            if len(table_a[key]) > len(table_b[key]):
                                update_dict[key] = table_a[key]
                            else:
                                update_dict[key] = table_b[key]

                    elif key == "team":
                        update_dict[key] = table_b[key]

                    elif key == "name":
                        update_dict[key] = table_b[key]

                    else:
                        update_dict[key] = table_a[key] + table_b[key]
            else:
                update_dict[key] = table_a[key]

        #loop over table_b for any keys that are in b but not a
        for key in table_b:
            if key not in table_a and key is not None:
                update_dict[key] = table_b[key]

        return update_dict

    def add_player_names(self, stat_dict):
        if self._name_table:
            for cid in self._name_table:
                if cid in stat_dict:
                    stat_dict[cid]["name"] = self._name_table[cid]

    def construct_stat_query(self):
        #constructs a select query from the STAT_KEYS dict, so we always know the order data is retrieved in
        #this means that new columns can be added to tables on the fly, while retaining a known format

        query = "SELECT %s FROM %s WHERE log_ident = '%s'" % (', '.join(stat_columns), DB_STAT_TABLE, self._unique_ident)

        return query

    def construct_team_stat_query(self):
        # construct the team stat select query using team stat keys
        #"SELECT team, SUM(kills), SUM(deaths), SUM(healing_done), SUM(overhealing_done), SUM(damage_dealt) FROM %s WHERE (log_ident = '%s' AND team IS NOT NULL) GROUP BY team" % (DB_STAT_TABLE, self._unique_ident)

        # get the col names from the team stat columns, which are prepended by team_
        # and put them in a list of SUM(col name)
        # we then join this list in the select query
        select_cols = [ "SUM(%s)" % x.replace("team_", "") for x in team_stat_columns ]

        query = "SELECT team, %s FROM %s WHERE (log_ident = '%s' AND team IS NOT NULL) GROUP BY team" % (', '.join(select_cols), DB_STAT_TABLE, self._unique_ident)

        return query

    def get_database_updates(self):
        #executes the queries to obtain updates. called periodically
        self.log.info("Getting database update for log %s", self._unique_ident)        

        # if we don't have a recent chat event, perform the default query.
        # else, we perform a query based on the current id, so that we
        # do not get chat duplicates
        if not self._chat_event_id:
            chat_query = self._default_chat_query
        else:
            chat_query = "SELECT id, name, team, chat_type, chat_message FROM %s WHERE id > '%d' AND log_ident = '%s'" % (DB_CHAT_TABLE, self._chat_event_id, self._unique_ident)

        try:
            self.db.execute(self._stat_query, callback = self._stat_update_callback)
        except:
            self.log.exception("Exception occured during stat query")

        try:
            self.db.execute(chat_query, callback = self._chat_update_callback)
        except:
            self.log.exception("Exception occured during chat query")

        try:
            self.db.execute(self._score_query, callback = self._score_update_callback)
        except:
            self.log.exception("Exception occured during score query")

        try:
            self.db.execute(self._team_stat_query, callback = self._team_stat_update_callback)
        except:
            self.log.exception("Exception occured during team stat query")

        #we only need to perform a name query when we don't have enough names to match against all the players in the log
        if len(self._name_table) < len(self._stat_table):
            try:
                self.db.execute(self._name_query, callback = self._name_update_callback)
            except:
                self.log.exception("Exception occured during stat query")
        
    def _stat_update_callback(self, cursor, error):
        #the callback for stat update queries
        if error or not cursor:
            self.log.error("Error querying database for stat data: %s", error)
            return

        if self.ended:
            return
        
        self.log.debug("Stat update callback")

        try:
            new_stat = {}
            
            #iterate over the cursor, and convert it to a sensible dictionary
            temp_list = []

            for row in cursor:
                #each row is a player's data as a tuple in the format of:
                #SID:K:D:A:P:HD:HR:UU:UL: --- ETC
                
                temp_list.append(self.stat_tuple_to_dict(row)) #convert stat tuple to a dict that we then iterate over  
            
            new_stat = self.merge_stat_list(temp_list) #merge here, so all later tables will automatically use the merged dict

            if not self._stat_table: #if this is the first callback, make the complete table this dict
                self._stat_table = new_stat

            else:
                #we need to get the table difference between the previous complete set and the new dict before we update to the latest data
                temp_table = self.calc_table_delta(self._stat_table, new_stat)

                # if the new delta table is different to the previous table, update
                if temp_table != self._stat_difference_table:
                    if self._new_stat_update:
                        self.log.debug("There is a stat update waiting to be sent. Combining tables")
                        #there's already an update waiting to be sent. we should therefore combine updates
                        self._stat_difference_table = self.combine_update_table(temp_table, self._stat_difference_table)

                    else:
                        self._stat_difference_table = temp_table
                    
                    # update the full table to the new stats
                    self._stat_table = new_stat

                    self._new_stat_update = True

        except:
            self.log.exception("Exception during _stat_update_callback")

    def _team_stat_update_callback(self, cursor, error):
        if error or not cursor:
            self.log.error("Error querying team stats: %s", error)

            return

        if self.ended:
            return

        self.log.debug("Team stat update callback")

        try:
            team_stats = {}

            for row in cursor:
                self.log.debug("team update row: %s", row)
                team = row[0]

                if team != "None":
                    team = team.lower() # make sure the team name is lowercase
                    team_stats[team] = self.team_stat_tuple_to_dict(row[1:]) #splice the row so we just have the stats, and convert them to a dict

            if not self._team_stat_table:
                self._team_stat_table = team_stats

            else:
                #get table diff
                temp_table = self.calc_table_delta(old_table = self._team_stat_table, new_table = team_stats)

                #print("new delta update dict:")
                #pprint(temp_table)

                if temp_table != self._team_stat_difference_table:
                    if self._new_team_stat_update:
                        #combine the updates
                        self.log.debug("There is a team stat update waiting. Combining tables")
                        self._team_stat_difference_table = self.combine_update_table(temp_table, self._team_stat_difference_table)

                    else:
                        self._team_stat_difference_table = temp_table
                    
                    # update the full table to the new stats
                    self._team_stat_table = team_stats

                    #pprint(self._team_stat_difference_table)

                    self._new_team_stat_update = True

        except:
            self.log.exception("Exception during _team_stat_update_callback")
        
    def _chat_update_callback(self, cursor, error):
        if error or not cursor:
            self.log.error("Error querying database for chat data: %s", error)
            return

        if self.ended:
            return

        self.log.debug("Chat update callback")
        try:
            #if this is the first chat query, it is a query to get the most recent chat event id
            #subsequent queries will contain chat after this id
            if not self._chat_event_id:
                if cursor:
                    self._chat_event_id = cursor.fetchone()[0]
                    if self._chat_event_id: #may be None, if unable to get any results
                        self.log.debug("First chat query. Latest chat event id: %d", self._chat_event_id)
                else:
                    self.log.error("Invalid result for chat query: %s", cursor.fetchone())

            else:
                chat_dict = {}

                for row in cursor:
                    if len(row) < 5:
                        continue

                    #each row will be a tuple in the format of:
                    #id, name, team, chat_type, chat_message
                    self._chat_event_id = row[0] #set the latest chat event id

                    chat_id = row[0] #table row id

                    chat_dict[chat_id] = {
                            "name": row[1], 
                            "team": row[2], 
                            "msg_type": row[3], 
                            "msg": row[4]
                        }

                    self.log.debug("CHAT: ID: %s NAME: %s TEAM: %s MSG_TYPE: %s MSG: %s", row[0], row[1], row[2], row[3], row[4])

                if chat_dict:
                    if self._new_chat_update:
                        self.log.debug("There is a chat update waiting to be sent. Combining updates")

                        self._chat_table = self.combine_update_table(self._chat_table, chat_dict)

                    else: #no updates waiting, just assign the new dict
                        self._chat_table = chat_dict

                    self._new_chat_update = True

        except:
            self.log.exception("Exception during _chat_update_callback")

    def _score_update_callback(self, cursor, error):
        if error or not cursor:
            self.log.error("Error querying database for score data: %s", error)
            return

        if self.ended:
            return

        self.log.debug("Score update callback")

        #if there's data, data is in a tuple in the format: (red_score, blue_score)
        #or, it's in the format (null, null) and the scores are 0
        try:
            score_dict = {}

            scores = cursor.fetchone() #a single tuple in the format described above
            self.log.debug("Score query returned %s", scores)
            
            if scores and len(scores) >= 1: 
                if scores[0]:
                    score_dict["red"] = scores[0]
                else:
                    score_dict["red"] = 0

                if len(scores) >= 2:
                    if scores[1]:
                        score_dict["blue"] = scores[1]
                    else:
                        score_dict["blue"] = 0

                if not self._score_table:
                    self._score_table = score_dict
                    self.log.debug("FIRST SCORE UPDATE: Red: %d Blue: %d", score_dict["red"], score_dict["blue"])

                else:
                    score_diff_dict = self.calc_table_delta(self._score_table, score_dict)

                    if score_diff_dict:
                        if self._new_score_update:
                            self.log.debug("Score update waiting. Combining")

                            self._score_difference_table = self.combine_update_table(self._score_difference_table, score_diff_dict)
                        else:
                            self._score_difference_table = score_diff_dict


                        self._new_score_update = True
                    self._score_table = score_dict
                    
            else:
                self._score_table = {
                        "red": 0,
                        "blue": 0
                    }

        except:
            self.log.exception("Exception during _score_update_callback")

    def _name_update_callback(self, cursor, error):
        if error or not cursor:
            self.log.error("Error querying database for name data: %s", error)
            return

        if self.ended:
            return

        try:
            for row in cursor:
                #row in the form (name, steamid)
                self._name_table[row[1]] = row[0]

        except:
            self.log.exception("Exception during _name_update_callback")
        

    def get_heal_spread(self):
        if not self._stat_table:
            return {}

        # Want a per-team dict of who has received heals in a simple list of lists
        # that can be decoded and used straight away by clients
        heal_spread_values = {}
        heal_spread_colours = {}
        for cid in self._stat_table:
            pstat = self._stat_table[cid]
            team = pstat["team"]

            if (team is None or team == ""):
                continue
            
            if team not in heal_spread_values:
                heal_spread_values[team] = [["Player", "Heal %"]]

            if team not in heal_spread_colours:
                heal_spread_colours[team] = []

            pname = str(cid)
            if "name" in pstat:
                pname = pstat["name"]

            # Only send data if the player has received some healing
            if "healing_received" in pstat:
                heal_spread_values[team].append([ pname, pstat["healing_received"] ])

                heal_spread_colours[team].append({ "color": self._get_player_colour(cid, team)})


        self.log.debug("Got heal spread: %s", heal_spread_values)

        heal_spread = { "values": heal_spread_values, "colours": heal_spread_colours }

        return heal_spread

    def _get_player_colour(self, cid, team):
        if not team in self._player_colours:
            self._player_colours[team] = {}

        team_colours = self._player_colours[team]

        # make sure this player isn't duplicated in another team's colours
        # if they changed for whatever reason
        for t in self._player_colours:
            if t != team and cid in self._player_colours[t]:
                del self._player_colours[t][cid]
        
        if cid in team_colours:
            return team_colours[cid]

        # try to make sure this colour is unique until we run out of colours
        potential_colours = list(set(heal_pie_colours) - set(team_colours.values()))

        if len(potential_colours) == 0:
            self.log.error("NO colours left for player '%s' in team '%s'", cid, team)
            pprint(self._player_colours)

            # allow a duplicate colour
            potential_colours = heal_pie_colours

        pcolour = random.choice(potential_colours)

        # colour is (hopefully) unique!
        team_colours[cid] = pcolour

        return pcolour

    def cleanup(self):
        #the only cleanup we need to do is releasing the update thread and deleting data tables

        #del self._name_table
        #del self._chat_table
        #del self._stat_table
        #del self._team_stat_table
        #del self._score_table

        self.ended = True

        self.log.info("DB Manager ended")



