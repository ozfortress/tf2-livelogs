import threading
import logging
import time


"""
The database manager class holds copies of a log's data. It provides functions to calculate the difference between
currently stored data and new data (delta compression) which will be sent to the clients, along with time and chat data
"""
class dbManager(object):
    def __init__(self, log_id, db_conn, update_rate, end_callback = None):
        #end_callback is the function to be called when the log is no longer live
        
        self.log = logging.getLogger("dbManager #%s" % log_id)

        self.end_callback = end_callback
        self.LOG_IDENT = log_id
        self.db = db_conn
        self.update_rate = update_rate
        
        self.updateThread = None
        
        self.DB_STAT_TABLE = "log_stat_%s" % log_id
        self.DB_CHAT_TABLE = "log_chat_%s" % log_id
        self.DB_EVENT_TABLE = "log_event_%s" % log_id
        
        self._stat_difference_table = None #a dict containing the difference between stored and retrieved stat data, as dicts (_NOT_ TUPLES LIKE THE COMPLETE TABLE)
        self._stat_complete_table = None #a dict containing tuples of stat data with respect to steamids

        self._chat_table = None #a dict containing recent chat messages

        self._score_table = None #a dict containing the most recent scores
        self._score_difference_table = None #a dict containing the difference in score updates

        self._time_stamp = None #a variable containing the most recent timestamp available
        
        self._update_no_diff = 0
        self._log_status_check = False
        self._database_busy = False
        
        self._chat_event_id = 0 #maintain a copy of the last retreived chat event id
        self._time_event_id = 0 #last event id used for time

        self._stat_query_complete = False
        self._chat_query_complete = False
        self._score_query_complete = False
        self._time_query_complete = False

        self._new_stat_update = False
        self._new_chat_update = False
        self._new_score_update = False
        self._new_time_update = False

        self.STAT_KEYS = {
                0: "name",
                1: "kills",
                2: "deaths",
                3: "assists",
                4: "points",
                5: "heal_done",
                6: "heal_rcvd",
                7: "ubers_used",
                8: "ubers_lost",
                9: "headshots",
                10: "backstabs",
                11: "damage",
                12: "aps",
                13: "apm",
                14: "apl",
                15: "mks",
                16: "mkm",
                17: "mkl",
                18: "pointcaps",
                19: "pointblocks",
                20: "dominations",
                21: "t_dominated",
                22: "revenges",
                23: "suicides",
                24: "build_dest",
                25: "extinguish",
                26: "kill_streak",
            }

        self.updateThreadEvent = threading.Event()
        
        self.updateThread = threading.Thread(target = self._updateThread, args=(self.updateThreadEvent,))
        self.updateThread.daemon = True
        self.updateThread.start()
        
        #self.getDatabaseUpdate()
    
    def steamCommunityID(self, steam_id):
        #takes a steamid in the format STEAM_x:x:xxxxx and converts it to a 64bit community id
        
        auth_server = 0;
        auth_id = 0;
        
        steam_id_tok = steam_id.split(':')
        
        auth_server = int(steam_id_tok[1])
        auth_id = int(steam_id_tok[2])
        
        community_id = auth_id * 2 #multiply auth id by 2
        community_id += 76561197960265728 #add arbitrary number chosen by valve
        community_id += auth_server #add the auth server. even ids are on server 0, odds on server 1
        
        return community_id
    
    def statIdxToName(self, index):
        #converts an index in the stat tuple to a name for use in dictionary keys
        
        index_name = self.STAT_KEYS[index]
        #self.log "NAME FOR INDEX %d: %s" % (index, index_name)
        
        return index_name
    
    def statTupleToDict(self, stat_tuple):
        #takes a tuple in the form:
        #NAME:K:D:A:P:HD:HR:UU:UL:HS:BS:DMG:APsm:APmed:APlrg:MKsm:MKmed:MKlrg:CAP:CAPB:DOM:TDOM:REV:SUICD:BLD_DEST:EXTNG:KILL_STRK
        #and converts it to a simple dictionary
        
        stat_dict = {}
        
        for idx, val in enumerate(stat_tuple):
            if idx >= 1: #skip stat_tuple[0], which is the player's name
                if val > 0: #ignore zero values when sending updates
                    idx_name = self.statIdxToName(idx)
                    if idx == 4: #catch the points, which are auto converted Decimal, and aren't handled by tornado's json encoder
                        stat_dict[idx_name] = float(val)
                    else:
                        stat_dict[idx_name] = val
                    
        return stat_dict
    
    def firstUpdate(self):
        #constructs and returns a dictionary for a complete update to the client
        
        #_stat_complete_table has keys consisting of player's steamids, corresponding to their stats as a tuple in the form:
        #NAME:K:D:A:P:HD:HR:UU:UL:HS:BS:DMG:APsm:APmed:APlrg:MKsm:MKmed:MKlrg:CAP:CAPB:DOM:TDOM:REV:SUICD:BLD_DEST:EXTNG:KILL_STRK
        #we need to convert this to a dictionary, so it can be encoded as json by write_message, and then easily decoded by the client
        
        update_dict = {}
        
        stat_dict = {}

        if self._stat_complete_table:
            for steam_id in self._stat_complete_table:
                stat_dict[steam_id] = self.statTupleToDict(self._stat_complete_table[steam_id])

        update_dict["stat"] = stat_dict

        if self._score_table:
            update_dict["score"] = self._score_table

        return update_dict
    
    def compressedUpdate(self):
        #returns a dictionary for a delta compressed update to the client
        update_stat_dict = {}

        if self._stat_difference_table:
            for steam_id in self._stat_difference_table:
                player_stat_dict = self._stat_difference_table[steam_id]
                if player_stat_dict: #if the dict is not empty
                    update_stat_dict[steam_id] = player_stat_dict #add it to the stat update dict
                
        update_dict = {}

        if update_stat_dict and self._new_stat_update:
            self.log.info("Have stat update diff in compressedUpdate")
            update_dict["stat"] = update_stat_dict

            self._new_stat_update = False

        if self._chat_table and self._new_chat_update:
            self.log.info("Have chat update dict in compressedUpdate")
            update_dict["chat"] = self._chat_table
            self._chat_table = None #clear the chat table, so it cannot be duplicated on next send if update fails

            self._new_chat_update = False

        if self._score_difference_table and self._new_score_update:
            self.log.info("Have score update dict in compressedUpdate")
            update_dict["score"] = self._score_difference_table

            self._score_difference_table = None #clear score table to prevent duplicates
            self._new_score_update = False

        if self._time_stamp and self._new_time_update:
            update_dict["gametime"] = self._time_stamp

            self._time_stamp = None
            self._new_time_update = False

        return update_dict
    
    def updateStatTableDifference(self, old_table, new_table):
        #calculates the difference between the currently stored data and an update
        #tables in the form of dict[sid] = tuple of stats
        
        stat_dict_updated = {}
        
        for steam_id in new_table:
            new_stat_tuple = new_table[steam_id]
            
            if steam_id in old_table:
                #steam_id is in the old table, so now we need to find the difference between the old and new tuples
                old_stat_tuple = old_table[steam_id]
                
                
                temp_list = [] #temp list that will be populated with all the stat differences, and then converted to a tuple
                
                #first we need to initialise the temp_list so we can access it by index
                for i in range(len(new_stat_tuple)):
                    temp_list.append(0)
                
                #now we have two tuples with identical lengths, and possibly identical values
                for idx, val in enumerate(new_stat_tuple):
                    if idx >= 1:
                        diff = val - old_stat_tuple[idx] #we have the difference between two values of the same index in the tuples
                        
                        temp_list[idx] = diff #store the new value in the temp tuple
                    else:
                        if val != old_stat_tuple[0]:
                            temp_list[idx] = val #idx 0 is the name, you can't get the difference, but you can simply assign the name regardless of if it's different
                
                stat_dict_updated[steam_id] = self.statTupleToDict(tuple(temp_list)) #add the diff'd stat dict to the diff table
                
            else: #steam_id is present in the new table, but not old. therefore it is new and doesn't need to have the difference found
                stat_dict_updated[steam_id] = self.statTupleToDict(new_stat_tuple)
                
        return stat_dict_updated
    
    def combineUpdateTable(self, old_table, new_table):
        #this will add two dictionaries together in the case that two updates occur before data is sent

        update_dict = {}

        for key in new_table:
            if key in old_table:
                #table[key] can be another dict in the case of stat updates, because there's dicts with steamids, and then corresponding stats
                if isinstance(new_table[key], dict) and isinstance(old_table[key], dict): #it's a stat update with key == steamid
                    update_dict[key] = self.combineUpdateTable(old_table[key], new_table[key]) #recursively combine the lower levels
                else:
                    update_dict[key] = new_table[key] + old_table[key]
            else:
                update_dict[key] = new_table[key]

        for key in old_table:
            if key not in new_table:
                update_dict[key] = old_table[key]

        return update_dict


    def getDatabaseUpdate(self):
        #executes the queries to obtain updates. called periodically
        if self._log_status_check == True:
            self.log.info("Currently checking log status. Waiting before more updates")
            return
        
        if not self.updateThread.isAlive():
            self.updateThread.start()
            
        i = 0
        for conn in self.db._pool:
            if not conn.busy():
                i += 1
            
        self.log.info("Number of non-busy pSQL connections: %d", i)
            
        if self._update_no_diff > 10:
            self.log.info("Had 10 updates since there's been a difference. Checking log status")

            self._log_status_check = True
            
            try:
                self.db.execute("SELECT live FROM livelogs_servers WHERE log_ident = %s", (self.LOG_IDENT,), callback = self._databaseStatusCallback)
                
            except psycopg2.OperationalError:
                self.log.info("Operational error during log status check")
                self._log_status_check = False
                
            except Exception as e:
                self.log.info("Unknown exception %s occurred during database update", e)
                
        elif not self._database_busy:    
            self.log.info("Getting database update on table %s", self.DB_STAT_TABLE)
            
            self._database_busy = True

            self._stat_query_complete = False
            self._chat_query_complete = False
            self._score_query_complete = False
            self._time_query_complete = False
            
            stat_query = "SELECT * FROM %s" % self.DB_STAT_TABLE
            if not self._chat_event_id:
                chat_query = "SELECT MAX(eventid) FROM %s" % self.DB_CHAT_TABLE #need to get the most recent id for first update, to prevent chat duplicates
            else:
                chat_query = "SELECT * FROM %s WHERE eventid > '%d'" % (self.DB_CHAT_TABLE, self._chat_event_id)

            score_query = "SELECT COALESCE(round_red_score, 0), COALESCE(round_blue_score, 0) FROM %s WHERE round_red_score IS NOT NULL AND round_blue_score IS NOT NULL ORDER BY eventid DESC LIMIT 1" % self.DB_EVENT_TABLE
            time_query = "SELECT event_time FROM %s WHERE eventid = '1' UNION SELECT event_time FROM %s WHERE eventid = (SELECT MAX(eventid) FROM %s)" % (self.DB_EVENT_TABLE, self.DB_EVENT_TABLE, self.DB_EVENT_TABLE)

            try:
                self.db.execute(stat_query, callback = self._databaseStatUpdateCallback)
                self.db.execute(chat_query, callback = self._databaseChatUpdateCallback)
                self.db.execute(score_query, callback = self._databaseScoreUpdateCallback)
                self.db.execute(time_query, callback = self._databaseTimeUpdateCallback)

            except psycopg2.OperationalError:
                self._database_busy = False
                
                self.log.info("Op error during database update")
                
            except Exception, e:
                self._database_busy = False
                
                self.log.exception("Unknown exception occurred during database update")
        else:
            self.log.info("Busy getting database updates")
            
    def _databaseStatusCallback(self, cursor, error):
        if error:
            self.log.info("Error querying database for log status: %s", error)
            self._log_status_check = False
            return
            
        self.log.info("databaseStatusCallback")   
        
        try:
            if cursor:
                result = cursor.fetchone()
                
                if result and len(result) > 0:
                    live = result[0]
                    
                    if (live == True):
                        self._update_no_diff = 0 #reset the increment, because the log is actually still live
                        self._log_status_check = False
                        
                        self.log.info("Log is still live. Continuing to update")
                    else:
                        #the log is no longer live
                        self.log.info("Log is no longer live")
                        self.cleanup()
                        
                        self.end_callback(self.LOG_IDENT)

        except Exception, e:
            self.log.exception("Exception during databaseStatusCallback")
        
    def _databaseStatUpdateCallback(self, cursor, error):
        #the callback for stat update queries
        if error:
            self.log.info("Error querying database for stat data: %s", error)
            self._stat_query_complete = True
            self.checkManagerBusyStatus()
            return
        
        self.log.info("Stat update callback")

        try:
            stat_dict = {}
            
            #iterate over the cursor
            for row in cursor:
                #each row is a player's data as a tuple in the format of:
                #SID:NAME:K:D:A:P:HD:HR:UU:UL:HS:BS:DMG:APsm:APmed:APlrg:MKsm:MKmed:MKlrg:CAP:CAPB:DOM:TDOM:REV:SUICD:BLD_DEST:EXTNG:KILL_STRK
                sid = self.steamCommunityID(row[0]) #player's steamid as a community id
                stat_dict[sid] = row[1:] #splice the rest of the data and store it under the player's steamid
                
            
            if not self._stat_complete_table: #if this is the first callback
                self._stat_complete_table = stat_dict
            else:
                #we need to get the table difference before we update to the latest data
                temp_table = self.updateStatTableDifference(self._stat_complete_table, stat_dict)
                if temp_table == self._stat_difference_table:
                    self._update_no_diff += 1 #increment number of times there's been an update with no difference

                else:
                    if self._new_stat_update:
                        self.log.info("There is a stat update waiting to be sent. Combining tables")
                        #there's already an update waiting to be sent. we should therefore combine updates
                        self._stat_difference_table = self.combineUpdateTable(temp_table, self._stat_difference_table)

                    else:
                        self._stat_difference_table = temp_table
                        self._stat_complete_table = stat_dict

                    self._new_stat_update = True

        except Exception, e:
            self.log.exception("Exception during _databaseStatUpdateCallback")
                
        self._stat_query_complete = True

        self.checkManagerBusyStatus()
        
    def _databaseChatUpdateCallback(self, cursor, error):
        if error:
            self.log.info("Error querying database for chat data: %s", error)
            self._chat_query_complete = True
            self.checkManagerBusyStatus()
            return

        self.log.info("Chat update callback")
        try:
            #if this is the first chat query, it is a query to get the most recent chat event id
            #subsequent queries will contain chat after this id
            if not self._chat_event_id:
                if cursor:
                    self._chat_event_id = cursor.fetchone()[0]
                    if self._chat_event_id: #may be None, if unable to get any results
                        self.log.info("First chat query. Latest chat event id: %d", self._chat_event_id)
                else:
                    self.log.info("Invalid result for chat query: %s", cursor.fetchone())

            else:
                chat_dict = {}

                for row in cursor:
                    #each row will be a tuple in the format of:
                    #eventid:steamid:name:team:chat_type:chat_msg
                    self._chat_event_id = row[0] #set the latest chat event id

                    sid = self.steamCommunityID(row[1]) #convert to community id

                    chat_dict[sid] = {
                            "name": row[2], 
                            "team": row[3], 
                            "msg_type": row[4], 
                            "msg": row[5]
                        }

                    self.log.info("CHAT: ID: %s NAME: %s TEAM: %s MSG_TYPE: %s MSG: %s", sid, row[2], row[3], row[4], row[5])

                if chat_dict:
                    if self._new_chat_update:
                        self.log.info("There is a chat update waiting to be sent. Combining updates")

                        self._chat_table = self.combineUpdateTable(self._chat_table, chat_dict)

                    else: #no updates waiting, just assign the new dict
                        self._chat_table = chat_dict

                    self._new_chat_update = True

        except Exception, e:
            self.log.exception("Exception during _databaseChatUpdateCallback")

        self._chat_query_complete = True

        self.checkManagerBusyStatus()

    def _databaseScoreUpdateCallback(self, cursor, error):
        if error:
            self.log.info("Error querying database for score data: %s", error)
            self._score_query_complete = True
            self.checkManagerBusyStatus()
            return

        self.log.info("Score update callback")

        #if there's data, data is in a tuple in the format: (red_score, blue_score)
        #or, it's in the format (null, null) and the scores are 0
        try:
            score_dict = {}

            scores = cursor.fetchone() #a single tuple in the format described above
            self.log.info("Score query returned %s", scores)
            
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
                    self.log.info("FIRST SCORE UPDATE: Red: %d Blue: %d", score_dict["red"], score_dict["blue"])

                else:
                    score_diff_dict = {}
                    for team in score_dict:
                        #score_dict has the most recent version
                        score_diff = score_dict[team] - self._score_table[team]
                        if score_diff:
                            score_diff_dict[team] = score_diff

                    if score_diff_dict:
                        if self._new_score_update:
                            self.log.info("Score update waiting. Combining")

                            self._score_difference_table = self.combineUpdateTable(self._score_difference_table, score_diff_dict)
                        else:
                            self._score_difference_table = score_diff_dict


                        self._new_score_update = True
                    self._score_table = score_dict
                    
            else:
                self._score_table = {
                        "red": 0,
                        "blue": 0
                    }

        except Exception, e:
            self.log.exception("Exception during _databaseScoreUpdateCallback")

        self._score_query_complete = True

        self.checkManagerBusyStatus()

    def _databaseTimeUpdateCallback(self, cursor, error):
        if error:
            self.log.info("Error querying database for time data: %s", error)
            self._time_query_complete = True
            self.checkManagerBusyStatus()
            return

        self.log.info("Time update callback")

        #if there's data, data will be in the format (2 tuples inside a tuple): ((start_time,), (most_recent_time,))
        #times are in the format "10/01/2012 21:38:18", so we need to convert them to epoch to get the difference
        try:
            times = cursor.fetchall() #two tuples in the format above
            self.log.info("Time query returned %s", times)

            if len(times) == 2:
                if (len(times[0]) > 0) and (len(times[1]) > 0): #we have our expected results!
                    time_format = "%m/%d/%Y %H:%M:%S"

                    start_time = time.mktime(time.strptime(times[0][0], time_format))

                    latest_time =time.mktime(time.strptime(times[1][0], time_format))

                    #time_diff is in seconds as a float
                    time_diff =  latest_time - start_time

                    #self.log.info("Time update difference: %0.2f", time_diff)

                    self._time_stamp = time_diff

                    self._new_time_update = True

        except Exception, e:
            self.log.exception("Exception during _databaseTimeUpdateCallback")
            
        self._time_query_complete = True

        self.checkManagerBusyStatus()

    def checkManagerBusyStatus(self):
        if self._database_busy:
            if self._stat_query_complete and self._score_query_complete and self._time_query_complete and self._chat_query_complete:
                self._database_busy = False

    def _updateThread(self, event):
        #this method is run in a thread, and acts as a timer. 
        #it is a daemon thread, and will exit cleanly with the main thread unlike a threading.Timer. 
        #it is also repeating, unlike a timer
        
        while not event.is_set(): #support signaling via an event to end the thread
            self.getDatabaseUpdate()
            
            event.wait(self.update_rate)

    def cleanup(self):
        #the only cleanup we need to do is releasing the update thread
        
        #NOTE: WE DO ____NOT____ CLOSE THE DATABASE. IT IS THE MOMOKO POOL, AND IS RETAINED THROUGHOUT THE APPLICATION
        if self.updateThread.isAlive():
            self.updateThreadEvent.set()
            
            while self.updateThread.isAlive(): 
                self.updateThread.join(5)
                
            self.log.info("Database update thread successfully closed")
            
    def __del__(self):
        #make sure cleanup is run if the class is deconstructed randomly. update thread is a daemon thread, so it will exit on close
        self.cleanup()