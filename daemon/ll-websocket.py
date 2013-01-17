"""
Websocket stuff, for dynamic updating of stats and sourcetv 2d relay

"""
try:
    import tornado
    import tornado.options
    import tornado.websocket
    import tornado.web
    import tornado.ioloop
    import tornado.escape
    from tornado import gen
except ImportError:
    print """You are missing tornado. 
    Install tornado using `pip install tornado`, or visit http://www.tornadoweb.org/
    """
    quit()
    
import logging
import time
import threading
import ConfigParser

from pprint import pprint

try:
    import momoko
except ImportError:
    print """Momoko is missing from the daemon directory, or is not installed in the python library
    Visit https://github.com/FSX/momoko to obtain the latest revision
    """
    
    quit()
    
logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

class llWSApplication(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/logupdate", logUpdateHandler),
            (r"/webrelay", webtvRelayHandler),
        ]
        
        settings = dict(
            cookie_secret = "12345",
        )
        
        tornado.web.Application.__init__(self, handlers, **settings)
        
class webtvRelayHandler(tornado.websocket.WebSocketHandler):
    pass
        
class logUpdateHandler(tornado.websocket.WebSocketHandler):
    clients = set() #set of ALL connected clients
    ordered_clients = { "none" : set() } #ordered clients dict will have data in the form of: [ "log ident": (client, client, client) ], where the clients are in a set corresponding to
                                         #the log ident sent by the client. new clients are added to "none" upon connection, and moved when a log ident is received
    
    cache = [] #holds a set of tuples containing log idents, the last time they were updated, and the status (live/not live) | [(cache_time, log_ident, status<t/f>), (cache_time, log_ident, status<t/f>)]
    
    db_managers = {} #a dictionary containing dbManager objects corresponding to log ids
    
    logUpdateThread = None
    
    #def allow_draft76(self):
        #allow old versions of the websocket protocol, for legacy support. LESS SECURE
    #    return True
    
    def __init__(self, application, request, **kwargs):
        self.LOG_IDENT_RECEIVED = False
        self.LOG_IDENT = None
        
        self.HAD_FIRST_UPDATE = False
        
        logUpdateHandler.update_rate = application.update_rate
        
        logUpdateHandler.logUpdateThreadEvent = threading.Event()
        
        logUpdateHandler.logUpdateThread = threading.Thread(target = logUpdateHandler._sendUpdateThread, args=(logUpdateHandler.logUpdateThreadEvent,))
        logUpdateHandler.logUpdateThread.daemon = True
        
        tornado.websocket.WebSocketHandler.__init__(self, application, request, **kwargs)
    
    def open(self):
        #client connects
        """
        This is a bit confusing. We add the client object to a set of objects, so it can later be accessed to send messages (and the connection will be maintained).
        All class variables (clients, log_idents, cache, etc) are required to be global accross the objects, so we add it to the classes' set, which all clients inherit
        
        Hence, if we have a function that iterates over the client set, we can access each client's connection object and send messages
        
        A new object is created for every new client
        """
        
        #inherits object "request" (which is a HTTPRequest object defined in tornado.httpserver) from tornado.web.RequestHandler
        logger.info("Client connected. IP: %s", self.request.remote_ip)
        
        logUpdateHandler.clients.add(self)
        logUpdateHandler.ordered_clients["none"].add(self)
        
    def on_close(self):
        #client disconnects
        logger.info("Client disconnected. IP: %s", self.request.remote_ip)
        logUpdateHandler.clients.remove(self)
        
        if (len(logUpdateHandler.clients) == 0) and logUpdateHandler.logUpdateThread.isAlive():
            #no clients are connected. stop the update thread
            logUpdateHandler.logUpdateThreadEvent.set()
            
            #while logUpdateHandler.logUpdateThread.isAlive():
            #    logUpdateHandler.logUpdateThread.join(5)
                
            
            logger.info("Ended sending update thread. No clients connected")

        logUpdateHandler.removeFromOrderedClients(self)
        

        return
        
    def on_message(self, msg):
        #client will send the log ident upon successful connection
        logger.info("Client %s sent msg: %s", self.request.remote_ip, msg)
        
        if (self.LOG_IDENT_RECEIVED):
            logger.info("Client %s has already sent log ident \"%s\"", self.request.remote_ip, self.LOG_IDENT)
            return
        
        #a standard message will be a json encoded message with key "ident"
        #i.e [ "ident" : 2315363_121212_1234567]
        try:
            parsed_msg = tornado.escape.json_decode(msg) 
            
        except ValueError:
            logger.info("ValueError trying to decode message")
            
            self.close()
            
            return
            
        log_id = parsed_msg["ident"]
        if not log_id:
            #invalid message received. IGNORE
            return
            
        log_cached = False
        
        self.LOG_IDENT_RECEIVED = True
        self.LOG_IDENT = str(log_id)
        
        log_id = str(log_id)
        
        logger.info("Received log ident '%s'. Checking cache", log_id)
        
        #now we check if the log id exists, and if the game is still live
        #first, check the cache. invalid log idents will never be in the cache
        for cache_info in logUpdateHandler.cache:
            #cache_info = (cache_time, log_ident, status<t/f>)
            #check for ident first
            logger.info("Cache info:")
            print cache_info
            
            if cache_info[1] == log_id:
                logger.info("Log ident is in the cache. Checking live status")
                log_cached = True
                
                #was the log live @ last cache? (logs will never go live again after ending)
                if (cache_info[2] == True):
                    #need to check if the cache is outdated
                    time_ctime = int(round(time.time()))
                    logger.info("Log id %s is cached as live", log_id)
                    
                    if ((time_ctime - cache_info[0]) > 60): #20 seconds have passed since last log check, so we need to refresh the cache
                        logger.info("Cache has expired for log id %s. Refreshing status", log_id)
                        
                        logUpdateHandler.removeFromCache(cache_info)
                        
                        self.getLogStatus(log_id)
                            
                    else:
                        #cached status is accurate enough
                        #add the client to the ordered_clients dict with correct log ident
                        logger.info("Cache for %s is recent. Using cached status", log_id)
                        
                        self.write_message("LOG_IS_LIVE") #notify client the log is live
                        
                        logUpdateHandler.addDBManager(log_id, self.application.db, self.application.update_rate)
                        logUpdateHandler.addToOrderedClients(log_id, self)
                        
                else:
                    #notify client the log is inactive, and close connection
                    
                    #TODO: Add something to prevent repeat invalid connections from same IP
                    
                    logger.info("Log id %s is not live. Closing connection", log_id)
                    
                    self.write_message("LOG_NOT_LIVE")
                    self.close()
                
                break
        
        #couldn't find the log in the cache, so it's either fresh or invalid
        if not log_cached:
            logger.info("Log id %s is not cached. Getting status", log_id)
            self.getLogStatus(log_id) #getLogStatus adds the ident to the cache if it is valid
        
    @classmethod
    def addToOrderedClients(cls, log_id, client):
        if log_id in cls.ordered_clients:
            #log_id key exists, just need client to add to set
            logger.info("log_id '%s' key exists. Adding client to list", log_id)
            cls.ordered_clients[log_id].add(client)
            
        else:
            #key doesn't exist with a set, so create the set and add the client to it
            logger.info("log_id '%s' key doesn't exist in ordered_clients. Creating", log_id)
            cls.ordered_clients[log_id] = set()
            cls.ordered_clients[log_id].add(client)
            
        cls.ordered_clients["none"].discard(client) #remove from unallocated set
        
        if not cls.logUpdateThread.isAlive():
            logger.info("Starting send update thread")
            
            cls.logUpdateThread.start()
        
        #cls.sendLogUpdates()
        
    @classmethod
    def removeFromOrderedClients(cls, client):
        for key, set in cls.ordered_clients.iteritems():
            #key is a log ident, and set is the set of clients listening for this log ident
            if client in set:
                logger.info("Client has key %s. Removing", key)
                
                set.remove(client)
                if (len(set) == 0) and (key != "none"):
                    logger.info("key %s has empty set. deleting key", key)
                    del cls.ordered_clients[key]
                    
                    #we know the set is now empty of clients, so we don't need the dbManager for this log id anymore
                    cls.delDBManager(key)
                    
                break
        
    @classmethod    
    def addToCache(cls, log_ident, status):
        #cache_info = (cache_time, log_ident, status<t/f>)
        cls.cache.append((int(round(time.time())), log_ident, status))
        
    @classmethod
    def removeFromCache(cls, cache_item):
        cls.cache.remove(cache_item) #cache_item has same structure as shown in the addToCache method
        
        logger.info("Removed cache item (%s, %s, %s)", cache_item[0], cache_item[1], cache_item[2])
    
    @classmethod
    def addDBManager(cls, log_ident, database, update_rate):
        if log_ident not in cls.db_managers:
            logger.info("Adding %s to dbManager dict", log_ident)
            #now we need to create a new dbManager for this log id. the database handle is the momoko pool created @ startup
            #and is the same for all clients
            cls.db_managers[log_ident] = dbManager(log_ident, database, update_rate, end_callback = cls._logFinishedCallback)
    
    @classmethod
    def delDBManager(cls, log_ident):
        if log_ident in cls.db_managers:
            #log_ident key in db_managers corresponds to a dbManager object
            
            logger.info("Cleaning up dbManager object for log id %s", log_ident)
            cls.db_managers[log_ident].cleanup() #run the cleanup method, which ends the update thread. everything else is garbage collected
            
            logger.info("Removing dbManager object for log id %s", log_ident)
            del cls.db_managers[log_ident]
    
    @classmethod
    def sendLogUpdates(cls):
        if len(cls.clients) == 0:
            logger.info("Sending thread is still active, but no clients are connected")
            #there's nothing we can do from here to stop the thread, as this method is being invoked by the thread and is part of it
            #hence, it cannot be joined by this method or have the event set by this method
            #something in the main thread must ensure that the send thread is paused

            return
        
        logger.info("Sending updates. Number of clients: %d", len(cls.clients))
        for log_id in cls.ordered_clients:
            if log_id != "none":
                #the key will correspond to a set of client objects which are listening for updates on this log id
                
                for client in cls.ordered_clients[log_id]:
                    #client is a websocket client object, which data can be sent to using client.write_message, etc
                    #client.write_message("HELLO!")
                    
                    if not client.HAD_FIRST_UPDATE:
                        #need to send complete values on first update to keep clients in sync with the server
                        if log_id in cls.db_managers:
                            #if we have data yet
                            if cls.db_managers[log_id]._stat_complete_table and cls.db_managers[log_id]._score_table:
                                #send a complete update to the client
                                client.write_message(cls.db_managers[log_id].firstUpdate())
                                
                                client.HAD_FIRST_UPDATE = True
                            
                    else:
                        if log_id in cls.db_managers:
                            if cls.db_managers[log_id]._stat_difference_table:
                                delta_update_dict = cls.db_managers[log_id].compressedUpdate()
                                if delta_update_dict: #if the dict is not empty, send it. else, just keep processing and waiting for new update
                                    client.write_message(delta_update_dict)

    def getLogStatus(self, log_ident):
        """
        Executes the query to obtain the log status
        """
        
        i = 0
        for conn in self.application.db._pool:
            if not conn.busy():
                i += 1
        
        logger.info("Number of non-busy pSQL conns @ getLogStatus: %d", i)
        
        self.application.db.execute("SELECT live FROM livelogs_servers WHERE log_ident = %s", (log_ident,), callback=self._logStatusCallback)
    
    @tornado.web.asynchronous
    def _logStatusCallback(self, cursor, error):
        if error:
            self.write_message("LOG_ERROR")
            logger.info("Error querying database for log status")
            
            self.close()
            return
        
        #if live is NOT NULL, then the log exists
        #live == t means the log is live, and live == f means it's not live
        
        results = cursor.fetchone() #fetchone returns a list, we only have 1 element and it'll be the first (idx 0)
        
        if results and len(results) > 0:
            live = results[0]
        
            if live == True:
                #add the client to the ordered_clients dict with correct log ident
                logger.info("Log %s is live on refreshed status", self.LOG_IDENT)
                self.write_message("LOG_IS_LIVE") #notify client the log is live
                
                logUpdateHandler.addToCache(self.LOG_IDENT, True)
                logUpdateHandler.addDBManager(self.LOG_IDENT, self.application.db, self.application.update_rate)
                logUpdateHandler.addToOrderedClients(self.LOG_IDENT, self)
                
            elif live == False:
                logger.info("Log %s is not live", self.LOG_IDENT)
                logUpdateHandler.addToCache(self.LOG_IDENT, False)
                
                self.closeLogUpdate()
                
            else:
                self.closeLogUpdate()
        else:
            self.closeLogUpdate()
                
    def closeLogUpdate(self):
        self.write_message("LOG_NOT_LIVE")
        
        self.close()
    
    @classmethod
    def _sendUpdateThread(cls, event):
        #this method is run in a thread, and acts as a timer
        while not event.is_set():
            event.wait(cls.update_rate)
            
            cls.sendLogUpdates()

    @classmethod
    def _logFinishedCallback(cls, log_ident):
        logger.info("Log id %s is over. Closing connections", log_ident)
        if log_ident in cls.ordered_clients:
            for client in cls.ordered_clients[log_ident]:
                client.write_message("END_LOG")
                
                client.close() #on_close will take care of empty sets and what not!
                
                cls.delDBManager(log_ident)
"""
The database manager class holds a copy of a log id's stat table. It provides functions to calculate the difference between
currently stored data and new data (delta compression) which will be sent to the clients.
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
        
        dict = {}
        
        for idx, val in enumerate(stat_tuple):
            if idx >= 1: #skip stat_tuple[0], which is the player's name
                if val > 0: #ignore zero values when sending updates
                    idx_name = self.statIdxToName(idx)
                    if idx == 4: #catch the points, which are auto converted Decimal, and aren't handled by tornado's json encoder
                        dict[idx_name] = float(val)
                    else:
                        dict[idx_name] = val
                    
        return dict
    
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

        if update_stat_dict:
            self.log.info("Have stat update diff in compressedUpdate")
            update_dict["stat"] = update_stat_dict

        if self._chat_table:
            self.log.info("Have chat update dict in compressedUpdate")
            update_dict["chat"] = self._chat_table
            pprint(update_dict["chat"])
            self._chat_table = None #clear the chat table, so it cannot be duplicated on next send if update fails

        if self._score_difference_table:
            self.log.info("Have score update dict in compressedUpdate")
            update_dict["score"] = self._score_difference_table

        if self._time_stamp:
            update_dict["gametime"] = self._time_stamp

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
                
            except Exception as e:
                self._database_busy = False
                
                self.log.info("Unknown exception %s occurred during database update", e)
        else:
            self.log.info("Busy getting database updates")
            
    def _databaseStatusCallback(self, cursor, error):
        if error:
            self.log.info("Error querying database for log status: %s", error)
            self._log_status_check = False
            return
            
        self.log.info("databaseStatusCallback")   
         
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
        
    def _databaseStatUpdateCallback(self, cursor, error):
        #the callback for stat update queries
        if error:
            self.log.info("Error querying database for stat data: %s", error)
            self._stat_query_complete = True
            self.checkManagerBusyStatus()
            return
        
        self.log.info("Stat update callback")

        stat_dict = {}
        
        #iterate over the cursor
        for row in cursor:
            #each row is a player's data as a tuple in the format of:
            #SID:NAME:K:D:A:P:HD:HR:UU:UL:HS:BS:DMG:APsm:APmed:APlrg:MKsm:MKmed:MKlrg:CAP:CAPB:DOM:TDOM:REV:SUICD:BLD_DEST:EXTNG:KILL_STRK
            sid = self.steamCommunityID(row[0]) #player's steamid as a community id
            stat_dict[sid] = row[1:] #splice the rest of the data and store it under the player's steamid
            
        
        if not self._stat_complete_table:
            self._stat_complete_table = stat_dict
        else:
            #we need to get the table difference before we update to the latest data
            temp_table = self.updateStatTableDifference(self._stat_complete_table, stat_dict)
            if temp_table == self._stat_difference_table:
                self._update_no_diff += 1 #increment number of times there's been an update with no difference

            else:
                self._stat_difference_table = temp_table
                self._stat_complete_table = stat_dict
            
        self._stat_query_complete = True

        self.checkManagerBusyStatus()
        
    def _databaseChatUpdateCallback(self, cursor, error):
        if error:
            self.log.info("Error querying database for chat data: %s", error)
            self._chat_query_complete = True
            self.checkManagerBusyStatus()
            return

        self.log.info("Chat update callback")

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

            self._chat_table = chat_dict

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

                self._score_difference_table = score_diff_dict
                self._score_table = score_dict
        else:
            self._score_table = {
                    "red": 0,
                    "blue": 0
                }

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

        times = cursor.fetchall() #two tuples in the format above
        self.log.info("Time query returned %s", times)

        if len(times) == 2:
            if (len(times[0]) > 0) and (len(times[1]) > 0): #we have our expected results!
                time_format = "%m/%d/%Y %H:%M:%S"

                start_time = time.mktime(time.strptime(times[0][0], time_format))

                latest_time =time.mktime(time.strptime(times[1][0], time_format))

                #time_diff is in seconds as a float
                time_diff =  latest_time - start_time

                self.log.info("Time update difference: %0.2f", time_diff)

                self._time_stamp = time_diff

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
            
if __name__ == "__main__": 
    cfg_parser = ConfigParser.SafeConfigParser()
    if cfg_parser.read(r'll-config.ini'):
        try:
            db_host = cfg_parser.get('database', 'db_host')
            db_port = cfg_parser.getint('database', 'db_port')
            db_user = cfg_parser.get('database', 'db_user')
            db_pass = cfg_parser.get('database', 'db_password')
            db_name = cfg_parser.get('database', 'db_name')
            
            server_ip = cfg_parser.get('websocket-server', 'server_ip')
            server_port = cfg_parser.getint('websocket-server', 'server_port')
            update_rate = cfg_parser.getfloat('websocket-server', 'update_rate')
            
        except:
            print "Unable to read websocket and or database section in config file. Please ensure you've run the daemon once, which generates the config file"
            quit()
    else:
        print "Error reading config file"
        quit()
    
    logger = logging.getLogger('WS MAIN')
    logger.info("Successfully read config")
    
    db_details = 'dbname=%s user=%s password=%s host=%s port=%s' % (
                db_name, db_user, db_pass, db_host, db_port)
    
    #support command line options, which will override whatever is set in the config
    tornado.options.define("ip", default=server_ip, help="Address the websocket server will listen on", type=str)
    tornado.options.define("port", default=server_port, help="Port the websocket server will listen on", type=int)
    tornado.options.define("update_rate", default=update_rate, help="The rate at which updates are pushed (seconds)", type=float)
    
    tornado.options.parse_command_line()
    
    llWebSocketServer = llWSApplication()
        
    llWebSocketServer.db = momoko.Pool(
        dsn = db_details,
        minconn = 2, #minimum number of connections for the momoko pool to maintain
        maxconn = 50, #max number of conns that will be opened
        cleanup_timeout = 10, #how often (in seconds) connections are closed (cleaned up) when number of connections > minconn
    )
    
    llWebSocketServer.update_rate = tornado.options.options.update_rate
    
    llWebSocketServer.listen(tornado.options.options.port, tornado.options.options.ip)
    logger.info("Websocket server listening on %s:%s", tornado.options.options.ip, tornado.options.options.port)
    
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        llWebSocketServer.db.close()
        tornado.ioloop.IOLoop.instance().stop()
        logger.info("Keyboard interrupt. Exiting")
        