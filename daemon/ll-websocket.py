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

from dbmanager import dbManager

from pprint import pprint

try:
    import momoko
except ImportError:
    print """Momoko is missing from the daemon directory, or is not installed in the python library
    Visit https://github.com/FSX/momoko to obtain the latest revision
    """
    
    quit()
    
logging.basicConfig(filename="websocket-server.log", level=logging.DEBUG, format="%(asctime)s - %(name)s (%(levelname)s): %(message)s", datefmt="%Y-%m-%d %H-%M-%S")

handler_logger = logging.getLogger("UPDATEHANDLER")
handler_logger.addHandler(logging.StreamHandler())

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
        
        if not logUpdateHandler.logUpdateThread:
            logUpdateHandler.logUpdateThreadEvent = threading.Event()
            
            logUpdateHandler.logUpdateThread = threading.Thread(target = logUpdateHandler._sendUpdateThread, args=(logUpdateHandler.logUpdateThreadEvent,))
            logUpdateHandler.logUpdateThread.daemon = True
            logUpdateHandler.logUpdateThread.start()

            handler_logger.info("Starting update thread")
        
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
        handler_logger.info("Client connected. IP: %s", self.request.remote_ip)
        
        logUpdateHandler.clients.add(self)
        logUpdateHandler.ordered_clients["none"].add(self)
        
    def on_close(self):
        #client disconnects
        handler_logger.info("Client disconnected. IP: %s", self.request.remote_ip)
        logUpdateHandler.clients.remove(self)

        logUpdateHandler.removeFromOrderedClients(self)
        

        return
        
    def on_message(self, msg):
        #client will send the log ident upon successful connection
        handler_logger.info("Client %s sent msg: %s", self.request.remote_ip, msg)
        
        if (self.LOG_IDENT_RECEIVED):
            handler_logger.info("Client %s has already sent log ident \"%s\"", self.request.remote_ip, self.LOG_IDENT)
            return
        
        #a standard message will be a json encoded message with key "ident"
        #i.e [ "ident" : 2315363_121212_1234567]
        try:
            parsed_msg = tornado.escape.json_decode(msg) 
            
        except ValueError:
            handler_logger.info("ValueError trying to decode message")
            
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
        
        handler_logger.info("Received log ident '%s'. Checking cache", log_id)
        
        #now we check if the log id exists, and if the game is still live
        #first, check the cache. invalid log idents will never be in the cache
        for cache_info in logUpdateHandler.cache:
            #cache_info = (cache_time, log_ident, status<t/f>)
            #check for ident first
            handler_logger.info("Cache info:")
            print cache_info
            
            if cache_info[1] == log_id:
                handler_logger.info("Log ident is in the cache. Checking live status")
                log_cached = True
                
                #was the log live @ last cache? (logs will never go live again after ending)
                if (cache_info[2] == True):
                    #need to check if the cache is outdated
                    time_ctime = int(round(time.time()))
                    handler_logger.info("Log id %s is cached as live", log_id)
                    
                    if ((time_ctime - cache_info[0]) > 60): #20 seconds have passed since last log check, so we need to refresh the cache
                        handler_logger.info("Cache has expired for log id %s. Refreshing status", log_id)
                        
                        logUpdateHandler.removeFromCache(cache_info)
                        
                        self.getLogStatus(log_id)
                            
                    else:
                        #cached status is accurate enough
                        #add the client to the ordered_clients dict with correct log ident
                        handler_logger.info("Cache for %s is recent. Using cached status", log_id)
                        
                        self.write_message("LOG_IS_LIVE") #notify client the log is live
                        
                        logUpdateHandler.addDBManager(log_id, self.application.db, self.application.update_rate)
                        logUpdateHandler.addToOrderedClients(log_id, self)
                        
                else:
                    #notify client the log is inactive, and close connection
                    
                    #TODO: Add something to prevent repeat invalid connections from same IP
                    
                    handler_logger.info("Log id %s is not live. Closing connection", log_id)
                    
                    self.write_message("LOG_NOT_LIVE")
                    self.close()
                
                break
        
        #couldn't find the log in the cache, so it's either fresh or invalid
        if not log_cached:
            handler_logger.info("Log id %s is not cached. Getting status", log_id)
            self.getLogStatus(log_id) #getLogStatus adds the ident to the cache if it is valid
        
    @classmethod
    def addToOrderedClients(cls, log_id, client):
        if log_id in cls.ordered_clients:
            #log_id key exists, just need client to add to set
            handler_logger.info("log_id '%s' key exists. Adding client to list", log_id)
            cls.ordered_clients[log_id].add(client)
            
        else:
            #key doesn't exist with a set, so create the set and add the client to it
            handler_logger.info("log_id '%s' key doesn't exist in ordered_clients. Creating", log_id)
            cls.ordered_clients[log_id] = set()
            cls.ordered_clients[log_id].add(client)
            
        cls.ordered_clients["none"].discard(client) #remove from unallocated set
        
    @classmethod
    def removeFromOrderedClients(cls, client):
        for key, set in cls.ordered_clients.iteritems():
            #key is a log ident, and set is the set of clients listening for this log ident
            if client in set:
                handler_logger.info("Client has key %s. Removing", key)
                
                set.remove(client)
                if (len(set) == 0) and (key != "none"):
                    handler_logger.info("key %s has empty set. deleting key", key)
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
        
        handler_logger.info("Removed cache item (%s, %s, %s)", cache_item[0], cache_item[1], cache_item[2])
    
    @classmethod
    def addDBManager(cls, log_ident, database, update_rate):
        if log_ident not in cls.db_managers:
            handler_logger.info("Adding %s to dbManager dict", log_ident)
            #now we need to create a new dbManager for this log id. the database handle is the momoko pool created @ startup
            #and is the same for all clients
            cls.db_managers[log_ident] = dbManager(log_ident, database, update_rate, end_callback = cls._logFinishedCallback)
    
    @classmethod
    def delDBManager(cls, log_ident):
        if log_ident in cls.db_managers:
            #log_ident key in db_managers corresponds to a dbManager object
            
            handler_logger.info("Cleaning up dbManager object for log id %s", log_ident)
            cls.db_managers[log_ident].cleanup() #run the cleanup method, which ends the update thread. everything else is garbage collected
            
            handler_logger.info("Removing dbManager object for log id %s", log_ident)
            del cls.db_managers[log_ident]
    
    @classmethod
    def sendLogUpdates(cls):
        if len(cls.clients) == 0:
            handler_logger.info("sendLogUpdates: No clients connected")

            return
        
        handler_logger.info("%d: Sending updates. Number of clients: %d", int(round(time.time())), len(cls.clients))
        for log_id in cls.ordered_clients:
            if log_id != "none":
                #the key will correspond to a set of client objects which are listening for updates on this log id
                
                for client in cls.ordered_clients[log_id]:
                    if client: #make sure the client still exists
                        #client is a websocket client object, which data can be sent to using client.write_message, etc
                        #client.write_message("HELLO!")
                        handler_logger.info("Checking for updates for client %s on id %s", client, log_id)
                        if log_id in cls.db_managers:
                            if not client.HAD_FIRST_UPDATE:
                            #need to send complete values on first update to keep clients in sync with the server
                                #if we have data yet
                                if cls.db_managers[log_id]._stat_complete_table and cls.db_managers[log_id]._score_table:
                                    #send a complete update to the client
                                    client.write_message(cls.db_managers[log_id].firstUpdate())
                                    
                                    client.HAD_FIRST_UPDATE = True
                                
                            else:
                                delta_update_dict = cls.db_managers[log_id].compressedUpdate()
                                handler_logger.info("Got update dict for %s", log_id)
                                if delta_update_dict: #if the dict is not empty, send it. else, just keep processing and waiting for new update
                                    handler_logger.info("Sending update to client %s", client)
                                    client.write_message(delta_update_dict)

    def getLogStatus(self, log_ident):
        """
        Executes the query to obtain the log status
        """
        
        i = 0
        for conn in self.application.db._pool:
            if not conn.busy():
                i += 1
        
        handler_logger.info("Number of non-busy pSQL conns @ getLogStatus: %d", i)
        

        #psycopg2 will automatically escape the string parameter, so we don't need to worry about sanity checking it for injections
        self.application.db.execute("SELECT live FROM livelogs_servers WHERE log_ident = %s", (log_ident,), callback=self._logStatusCallback)
    
    @tornado.web.asynchronous
    def _logStatusCallback(self, cursor, error):
        if error:
            self.write_message("LOG_ERROR")
            handler_logger.info("Error querying database for log status")
            
            self.close()
            return
        
        #if live is NOT NULL, then the log exists
        #live == t means the log is live, and live == f means it's not live
        
        results = cursor.fetchone() #fetchone returns a list, we only have 1 element and it'll be the first (idx 0)
        
        if results and len(results) > 0:
            live = results[0]
        
            if live == True:
                #add the client to the ordered_clients dict with correct log ident
                handler_logger.info("Log %s is live on refreshed status", self.LOG_IDENT)
                if self:
                    self.write_message("LOG_IS_LIVE") #notify client the log is live
                    
                    logUpdateHandler.addToCache(self.LOG_IDENT, True)
                    logUpdateHandler.addDBManager(self.LOG_IDENT, self.application.db, self.application.update_rate)
                    logUpdateHandler.addToOrderedClients(self.LOG_IDENT, self)
                
            elif live == False:
                handler_logger.info("Log %s is not live", self.LOG_IDENT)
                logUpdateHandler.addToCache(self.LOG_IDENT, False)
                
                self.closeLogUpdate()
                
            else:
                self.closeLogUpdate()
        else:
            self.closeLogUpdate()
                
    def closeLogUpdate(self):
        if self:
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
        handler_logger.info("Log id %s is over. Closing connections", log_ident)
        if log_ident in cls.ordered_clients:
            for client in cls.ordered_clients[log_ident]:
                client.write_message("LOG_END")
                
                client.close() #on_close will take care of empty sets and what not!
                
                cls.delDBManager(log_ident)
            
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
    logger.addHandler(logging.StreamHandler())

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
        