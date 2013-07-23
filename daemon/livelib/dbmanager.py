import threading
import logging
import time

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
            "ubers_used",
            "ubers_lost",
            "headshots",
            "damage_dealt",
            "damage_taken",
            "captures",
            "captures_blocked",
            "dominations"
        )


team_stat_columns = (
                "team_kills",
                "team_deaths",
                "team_healing_done",
                "team_damage_dealt",
                "team_damage_taken"
            )

"""
The database manager class holds copies of a log's data. It provides functions to calculate the difference between
currently stored data and new data (delta compression) which will be sent to the clients, along with time and chat data
"""
class dbManager(object):
    def __init__(self, db, log_id, db_lock, update_rate, start_time):
        #end_callback is the function to be called when the log is no longer live
        
        self.log = logging.getLogger(log_id)
        self.log.setLevel(logging.DEBUG)
        self.log.addHandler(log_file_handler)

        self.db = db
        self.database_lock = db_lock
        self.update_rate = update_rate
        self._unique_ident = log_id

        self.DB_STAT_TABLE = "livelogs_player_stats"
        self.DB_CHAT_TABLE = "livelogs_game_chat"
        self.DB_PLAYER_TABLE = "livelogs_player_details"
        self.DB_EVENT_TABLE = "log_event_%s" % log_id
        
        self._stat_table = None #a dict containing stat data
        self._stat_difference_table = None #a dict containing the difference between stored and retrieved stat data

        self._chat_table = None #a dict containing recent chat messages

        self._score_table = None #a dict containing the most recent scores
        self._score_difference_table = None #a dict containing the difference in score updates

        self._start_time = int(round(time.mktime(time.strptime(start_time, "%Y-%m-%d %H:%M:%S")))) #a variable containing the log start time in seconds since epoch
        
        self._team_stat_table = None #dict containing team stats
        self._team_stat_difference_table = None #dict containing team stat differences

        self._log_status_check = False
        self._database_busy = False
        
        self._chat_event_id = 0 #maintain a copy of the last retreived chat event id

        self._stat_query_complete = False
        self._chat_query_complete = False
        self._score_query_complete = False

        self._new_stat_update = False
        self._new_team_stat_update = False
        self._new_chat_update = False
        self._new_score_update = False

        self.updateThreadEvent = threading.Event()
        
        self.updateThread = threading.Thread(target = self._updateThread, args=(self.updateThreadEvent,))
        self.updateThread.daemon = True
        self.updateThread.start()

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
            if idx >= 1: #ignore the steamid, which is index 0
                if val > 0: #ignore zero values when sending updates
                    col = self.stat_idx_to_name(idx)
                    if col == "points": #catch the points, which are auto converted Decimal, and aren't handled by tornado's json encoder
                        stat_dict[col] = float(val)
                    else:
                        stat_dict[col] = val
                    
        return stat_dict

    def merge_stat_dict(self, stat_dict):
        #takes a stat dict with multiple entries per player and combines them on steamid
        merged_dict = {}

        for cid in stat_dict:
            curr_cid = cid

            if cid not in merged_dict:
                merged_dict[cid] = {}
        
            player_stat = stat_dict[cid] #cache the lower level of stat_dict for this iteration
            merged_stat = merged_dict[cid] #stats for this player

            for statcol in player_stat: #each cid in the stat_dict has a dict of stats, with table columns and values
                if statcol not in merged_stat:
                    #if the key doesn't exist in the merged dict, add it and assign the current value
                    merged_stat[statcol] = player_stat[statcol]

                else:
                    #if the key DOES exist in the merged dict, we have to either add the value or append a string depending on the column
                    if statcol == "class":
                        merged_stat[statcol] += ",%s" % player_stat[statcol]
                    elif statcol == "team":
                        if player_stat[statcol] is not None:
                            merged_stat[statcol] = player_stat[statcol]
                    else:
                        #just add the values together
                        merged_stat[statcol] += player_stat[statcol]

        pprint(merged_dict)

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

    def calc_table_delta(self, old_table, new_table, teams=False):
        """
        Calculates the delta update of two table dicts

        This means that we only want the difference between keys present in the old AND new tables, we don't care if a key is present in the old but not new.
        Keys present in the new table are included in the delta update, because they are clearly an update if they weren't previously present

        """
        
        diff_dict = {}
        
        for key in new_table:
            if key in old_table:
                #find the difference
                if isinstance(old_table[key], dict) and isinstance(new_table[key], dict): #keys are dicts, so we should do this recursively
                    diff_dict[key] = self.calc_table_delta(old_table[key], new_table[key])
                
                else:
                    #we get the difference by subtracting the old from the new

                    #special case for certain stat dict keys
                    #if the key is "team" and this is a team stat dict, we want to keep the team the same
                    if (key == "class" or key == "team"):
                        if (new_table[key] != old_table[key]) or teams:
                            diff_dict[key] = new_table[key]

                    else:
                        diff_dict[key] = new_table[key] - old_table[key]
                
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
                    update_dict[key] = table_a[key] + table_b[key]
            else:
                update_dict[key] = table_a[key]

        for key in table_b:
            if key not in table_a:
                update_dict[key] = table_b[key]

        return update_dict

    def construct_stat_query(self):
        #constructs a select query from the STAT_KEYS dict, so we always know the order data is retrieved in
        #this means that new columns can be added to tables on the fly, while retaining a known format

        query = "SELECT %s FROM %s WHERE log_ident = '%s'" % (', '.join(stat_columns), self.DB_STAT_TABLE, self._unique_ident)

        return query

    def get_database_updates(self):
        #executes the queries to obtain updates. called periodically
        self.log.info("Getting database update for log %s", self._unique_ident)

        self._stat_query_complete = False
        self._chat_query_complete = False
        self._score_query_complete = False
        
        stat_query = self.construct_stat_query()

        if not self._chat_event_id:
            chat_query = "SELECT MAX(id) FROM %s WHERE log_ident = '%s'" % (self.DB_CHAT_TABLE, self._unique_ident) #need to get the most recent id for first update, to prevent chat duplicates
        else:
            chat_query = "SELECT id, name, team, chat_type, chat_message FROM %s WHERE id > '%d' AND log_ident = '%s'" % (self.DB_CHAT_TABLE, self._chat_event_id, self._unique_ident)

        score_query = "SELECT COALESCE(round_red_score, 0), COALESCE(round_blue_score, 0) FROM %s WHERE round_red_score IS NOT NULL AND round_blue_score IS NOT NULL ORDER BY eventid DESC LIMIT 1" % (self.DB_EVENT_TABLE)

        team_stat_query = "SELECT team, SUM(kills), SUM(deaths), SUM(healing_done), SUM(damage_dealt), SUM(damage_taken) FROM %s WHERE log_ident = '%s' and team IS NOT NULL GROUP BY team" % (self.DB_STAT_TABLE, self._unique_ident)

        try:
            self.db.execute(stat_query, callback = self._stat_update_callback)
            self.db.execute(chat_query, callback = self._chat_update_callback)
            self.db.execute(score_query, callback = self._score_update_callback)
            self.db.execute(team_stat_query, callback = self._team_stat_update_callback)
            
        except:
            self.log.exception("Exception occurred during database update")

        finally:
            self._database_busy = False
        
    def _stat_update_callback(self, cursor, error):
        #the callback for stat update queries
        if error:
            self.log.error("Error querying database for stat data: %s", error)
            self._stat_query_complete = True
            self.__clear_busy_status()
            return
        
        self.log.debug("Stat update callback")

        try:
            new_stat = {}
            
            #iterate over the cursor, and convert it to a sensible dictionary
            for row in cursor:
                #each row is a player's data as a tuple in the format of:
                #SID:K:D:A:P:HD:HR:UU:UL: --- ETC
                cid = row[0] #player's steamid as a community id
                new_stat[cid] = self.stat_tuple_to_dict(row) #store stat data under steamid in dict  
            
            new_stat = self.merge_stat_dict(new_stat) #merge here, so all later tables will automatically use the merged dict

            if not self._stat_table: #if this is the first callback, make the complete table this dict
                self._stat_table = new_stat

            else:
                #we need to get the table difference between the previous complete set and the new dict before we update to the latest data
                temp_table = self.calc_table_delta(self._stat_table, new_stat)

                if temp_table != self._stat_difference_table:
                    if self._new_stat_update:
                        self.log.debug("There is a stat update waiting to be sent. Combining tables")
                        #there's already an update waiting to be sent. we should therefore combine updates
                        self._stat_difference_table = self.combine_update_table(temp_table, self._stat_difference_table)

                    else:
                        self._stat_difference_table = temp_table
                        self._stat_table = new_stat

                    self._new_stat_update = True

        except:
            self.log.exception("Exception during _stat_update_callback")
                
        self._stat_query_complete = True

        self.__clear_busy_status()

    def _team_stat_update_callback(self, cursor, error):
        if error:
            self.log.error("Error querying team stats: %s", error)

            return

        self.log.debug("Team stat update callback")

        try:
            team_stats = {}

            for row in cursor:
                team = row[0]
                team_stats[team] = self.team_stat_tuple_to_dict(row[1:]) #splice the row so we just have the stats, and convert them to a dict

            if not self._team_stat_table:
                self._team_stat_table = team_stats

            else:
                #get table diff
                temp_table = self.calc_table_delta(self._team_stat_table, team_stats, teams = True)

                if temp_table != self._team_stat_difference_table:
                    if self._new_team_stat_update:
                        #combine the updates
                        self._team_stat_difference_table = self.combine_update_table(team_stats, self._team_stat_difference_table)

                    else:
                        self._team_stat_difference_table = temp_table
                        self._team_stat_table = team_stats

                    self._new_team_stat_update = True

        except:
            self.log.exception("Exception during _team_stat_update_callback")
        
    def _chat_update_callback(self, cursor, error):
        if error:
            self.log.error("Error querying database for chat data: %s", error)
            self._chat_query_complete = True
            self.__clear_busy_status()
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

        self._chat_query_complete = True

        self.__clear_busy_status()

    def _score_update_callback(self, cursor, error):
        if error:
            self.log.error("Error querying database for score data: %s", error)
            self._score_query_complete = True
            self.__clear_busy_status()
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

        self._score_query_complete = True

        self.__clear_busy_status()

    def __clear_busy_status(self):
        if self._database_busy:
            if self._stat_query_complete and self._score_query_complete and self._time_query_complete and self._chat_query_complete:
                self._database_busy = False

    def _updateThread(self, event):
        #this method is run in a thread, and acts as a timer. 
        #it is a daemon thread, and will exit cleanly with the main thread unlike a threading.Timer. 
        #it is also repeating, unlike a timer
        
        while not event.is_set(): #support signaling via an event to end the thread
            self.database_lock.acquire() #acquire the lock, so only this manager can run the queries right now

            self.get_database_updates()

            self.database_lock.release()
            
            event.wait(self.update_rate)

    def cleanup(self):
        #the only cleanup we need to do is releasing the update thread and deleting the stat tables

        del self._stat_table
        del self._team_stat_table
        
        #NOTE: WE DO ____NOT____ CLOSE THE DATABASE. IT IS THE MOMOKO POOL, AND IS RETAINED THROUGHOUT THE APPLICATION
        if self.updateThread.isAlive():
            self.updateThreadEvent.set() #trigger the threading event, terminating the update thread
            
            #the join loop is so that we wait for the last update to run before closing the thread. we don't want the thread to remain running while the dbManager object is closed, so we need to wait
            while self.updateThread.isAlive(): 
                self.updateThread.join(5)
                
            self.log.info("Database update thread successfully closed")



