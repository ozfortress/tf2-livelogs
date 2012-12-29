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
    cache_size = 200 #max number of logs holdable
    
    db_managers = {} #a dictionary containing dbManager objects corresponding to log ids
    
    logger = logging.getLogger("CLIENTUPDATE")
    
    #def allow_draft76(self):
        #allow old versions of the websocket protocol, for legacy support. LESS SECURE
    #    return True
    def __init__(self, application, request, **kwargs):
        self.LOG_IDENT_RECEIVED = False
        self.LOG_IDENT = None
        
        self.HAD_FIRST_UPDATE = False
        
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
        
        print "Clients without ID:"
        print logUpdateHandler.ordered_clients["none"]
        
    def on_close(self):
        #client disconnects
        logger.info("Client disconnected. IP: %s", self.request.remote_ip)
        logUpdateHandler.clients.remove(self)
        
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
        
        cls.sendLogUpdates()
        
    @classmethod
    def removeFromOrderedClients(cls, client):
        for key, set in cls.ordered_clients.iteritems():
            if client in set:
                logger.info("Client has key %s. Removing", key)
                
                set.remove(client)
                if (len(set) == 0) and (key != "none"):
                    logger.info("key %s has empty set. deleting key", key)
                    del cls.ordered_clients[key]
                    
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
    def addDBManager(cls, log_ident, database):
        if not log_id in cls.db_managers:
            logger.info("Adding %s to dbManager dict", log_ident)
            #now we need to create a new dbManager for this log id. the database handle is the momoko pool created @ startup
            #and is the same for all clients
            cls.db_managers[log_ident] = dbManager(log_ident, database)
            
    
    @classmethod
    def sendLogUpdates(cls):
        for log_id in cls.ordered_clients:
            if log_id != "none":
                #the key will correspond to a set of client objects which are listening for updates on this log id
                
                
                for client in cls.ordered_clients[log_id]:
                    #client is a websocket client object, which data can be sent to using client.write_message, etc
                    client.write_message("HELLO!")
                    
                    if not client.HAD_FIRST_UPDATE:
                        if cls.db_managers[log_id].DB_LATEST_TABLE: #if we have a complete update available yet
                            #send a complete update to the client
                            client.write_message(cls.db_managers[log_id].fullUpdate())
                    
                    #for the sake of testing at the time being
                    client.close()
    
    def getLogStatus(self, log_ident):
        """
        Executes the query to obtain the log status
        """
        
        res_cursor = self.application.db.execute("SELECT live FROM livelogs_servers WHERE log_ident = %s", (log_ident,), callback=self._logStatusCallback)
    
    def _logStatusCallback(self, cursor, error):
        if error:
            self.write_message("LOG_ERROR")
            logger.info("Error querying database for log status")
            return
        
        #if live is NOT NULL, then the log exists
        #live == t means the log is live, and live == f means it's not live
        
        live = cursor.fetchone()[0] #fetchone returns a list, we only have 1 element and it'll be the first (idx 0)
        
        if live == True:
            #add the client to the ordered_clients dict with correct log ident
            logger.info("Log is live on refreshed status")
            self.write_message("LOG_IS_LIVE") #notify client the log is live
            
            logUpdateHandler.addToCache(self.LOG_IDENT, True)
            logUpdateHandler.addToOrderedClients(self.LOG_IDENT, self)
            
            logUpdateHandler.addDBManager(self.LOG_IDENT, self.application.db)
            
        elif live == False:

            self.write_message("LOG_NOT_LIVE")
            
            logger.info("Log is not live")
            
            logUpdateHandler.addToCache(self.LOG_IDENT, False)
            
            self.close()
                            
        else:                    
            #invalid log ident
            logger.info("Invalid log ident specified (live did not match true or false")
            self.write_message("LOG_NOT_LIVE")
            self.close()
            
        cursor.close()
        
"""
The database manager class holds a version of a log id's stat table. It provides functions to calculate the difference between
currently stored data and new data (delta compression) which will be sent to the clients.
"""
class dbManager(object):
    def __init__(self, log_id, db_conn):
        self.LOG_IDENT = log_id
        self.db = db_conn
        
        self.STAT_TABLE = "log_stat_" + log_id
        
        self.DB_DIFFERENCE_TABLE = None #a dict containing the difference between the stored data and 
        self.DB_LATEST_TABLE = None #a dict containing the most recently retrieved data
        
        self.getDatabaseUpdate()
    
    def statTupleToDict(self, stat_tuple):
        #takes a tuple in the form:
        #NAME:K:D:A:P:HD:HR:UU:UL:HS:BS:DMG:APsm:APmed:APlrg:MKsm:MKmed:MKlrg:CAP:CAPB:DOM:TDOM:REV:SUICD:BLD_DEST:EXTNG:KILL_STRK
        #and converts it to a simple dictionary
        
        #shortened names for extra network optimisation!
        dict = {
                "name": stat_tuple[0],
                "k": stat_tuple[1],
                "d": stat_tuple[2],
                "a": stat_tuple[3],
                "p": stat_tuple[4]
                "heald": stat_tuple[5],
                "healr": stat_tuple[6],
                "uu": stat_tuple[7],
                "ul": stat_tuple[8],
                "hs": stat_tuple[9],
                "bs": stat_tuple[10],
                "dmg": stat_tuple[11],
                "aps": stat_tuple[12],
                "apm": stat_tuple[13],
                "apl": stat_tuple[14],
                "mks": stat_tuple[15],
                "mkm": stat_tuple[16],
                "mkl": stat_tuple[17],
                "cp": stat_tuple[18],
                "cpb": stat_tuple[19],
                "dmn": stat_tuple[20],
                "tdmn": stat_tuple[21],
                "rvng": stat_tuple[22],
                "suicd": stat_tuple[23],
                "bdest": stat_tuple[24],
                "extng": stat_tuple[25],
                "kstrk": stat_tuple[26],
            }
        
        return dict
    
    def fullUpdate(self):
        #constructs and returns a dictionary for a complete update to the client
        
        #DB_LATEST_TABLE has keys consisting of player's steamids, corresponding to their stats as a tuple in the form:
        #NAME:K:D:A:P:HD:HR:UU:UL:HS:BS:DMG:APsm:APmed:APlrg:MKsm:MKmed:MKlrg:CAP:CAPB:DOM:TDOM:REV:SUICD:BLD_DEST:EXTNG:KILL_STRK
        #we need to convert this to a dictionary, so it can be encoded as json by write_message, and then easily decoded by the client
        
        update_dict = {}
        
        if self.DB_LATEST_TABLE:
            for steam_id, stat in self.DB_LATEST_TABLE:
                update_dict[steam_id] = self.statTupleToDict(stat)
        
        return update_dict
        
    def getTableDifference(self):
        #calculates the difference between the currently stored data and an update
        pass
        
    def getDatabaseUpdate(self):
        #executes the query to obtain an update. called on init and periodically
        
        query = "SELECT * FROM %s" % self.STAT_TABLE
        self.db.execute(query, callback = self._databaseUpdateCallback)
        
    def _databaseUpdateCallback(self, cursor, error):
        #the callback for database update queries
        if error:
            print "Error querying database for stat data on log id %s" % self.LOG_IDENT
            return
        
        stat_dict = {}
        
        print "Update callback for log id %s" % self.LOG_IDENT
        #iterate over the cursor
        for row in cursor:
            #each row is a player's data as a tuple in the format of:
            #SID:NAME:K:D:A:P:HD:HR:UU:UL:HS:BS:DMG:APsm:APmed:APlrg:MKsm:MKmed:MKlrg:CAP:CAPB:DOM:TDOM:REV:SUICD:BLD_DEST:EXTNG:KILL_STRK
            sid = row[0] #player's steamid
            stat_dict[sid] = row[1:] #splice the rest of the data and store it under the player's steamid
            
            print "steamid %s has data:" % sid
            print row[1:]
            
        self.DB_LATEST_TABLE = stat_dict
        
        #debug: run fullUpdate and print the dict
        
        print "Full update data:"
        pprint(self.fullUpdate())
        
        
            
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
            print "Unable to read websocket and or database section in config file"
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
        minconn = 1,
        maxconn = 50,
        cleanup_timeout = 10,
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
        