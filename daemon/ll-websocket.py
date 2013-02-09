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
import logging.handlers
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

log_message_format = logging.Formatter(fmt="[(%(levelname)s) %(process)s %(asctime)s %(module)s:%(name)s:%(lineno)s] %(message)s", datefmt="%H:%M:%S")

log_file_handler = logging.handlers.TimedRotatingFileHandler("websocket-server.log", when="midnight")
log_file_handler.setFormatter(log_message_format)
log_file_handler.setLevel(logging.DEBUG)

class llWSApplication(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/logupdate", logUpdateHandler),
            (r"/webrelay", webtvRelayHandler),
        ]
        
        settings = {
            "cookie_secret": "12345"
        }

        self.logger = logging.getLogger("WS APP")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(log_file_handler)
        
        self.log_clients = set() #set of ALL connected clients
        self.log_ordered_clients = { "none": set() } #ordered clients dict will have data in the form of: [ "log ident": (client, client, client) ], where the clients are in a set corresponding to
                                                #the log ident sent by the client. new clients are added to "none" upon connection, and moved when a log ident is received
        self.log_db_managers = {} #a dictionary containing dbManager objects corresponding to log ids

        self.log_cache = [] #holds a set of tuples containing log idents, the last time they were updated, and the status (live/not live) | [(cache_time, log_ident, status<t/f>), (cache_time, log_ident, status<t/f>)]

        self.log_update_thread_event = threading.Event()
        self.log_update_thread = threading.Thread(target = self._sendUpdateThread, args=(self.log_update_thread_event,))
        self.log_update_thread.daemon = True

        tornado.web.Application.__init__(self, handlers, **settings)
        
    def addToOrderedClients(self, log_id, client):
        if log_id in self.log_ordered_clients:
            #log_id key exists, just need client to add to set
            self.logger.debug("log_id '%s' key exists. Adding client to list", log_id)
            self.log_ordered_clients[log_id].add(client)
            
        else:
            #key doesn't exist with a set, so create the set and add the client to it
            self.logger.debug("log_id '%s' key doesn't exist in ordered_clients. Creating", log_id)
            self.log_ordered_clients[log_id] = set()
            self.log_ordered_clients[log_id].add(client)
            
        self.log_ordered_clients["none"].discard(client) #remove from unallocated set

        if not self.log_update_thread.isAlive():
            self.log_update_thread.start()
        
    def removeFromOrderedClients(self, client):
        for key, client_set in self.log_ordered_clients.iteritems():
            #key is a log ident, and set is the set of clients listening for this log ident
            if client in client_set:
                self.logger.debug("Client has key %s. Removing", key)
                
                client_set.remove(client)
                if (len(client_set) == 0) and (key != "none"):
                    self.logger.debug("key %s has empty set. deleting key", key)
                    del self.log_ordered_clients[key]
                    
                    #we know the set is now empty of clients, so we don't need the dbManager for this log id anymore
                    self.delDBManager(key)
                    
                break
            
    def addToCache(self, log_ident, status):
        #cache_info = (cache_time, log_ident, status<t/f>)
        self.log_cache.append((int(round(time.time())), log_ident, status))
        
    def removeFromCache(self, cache_item):
        self.log_cache.remove(cache_item) #cache_item has same structure as shown in the addToCache method
        
        self.logger.debug("Removed cache item (%s, %s, %s)", cache_item[0], cache_item[1], cache_item[2])
    
    def addDBManager(self, log_ident, database = None, update_rate = None):
        if log_ident not in self.log_db_managers:
            self.logger.debug("Adding %s to dbManager dict", log_ident)
            #now we need to create a new dbManager for this log id. the database handle is the momoko pool created @ startup
            #and is the same for all clients

            if not database:
                database = self.db
            if not update_rate:
                update_rate = self.update_rate

            self.log_db_managers[log_ident] = dbManager(log_ident, database, update_rate, end_callback = self._logFinishedCallback)
    
    def delDBManager(self, log_ident):
        if log_ident in self.log_db_managers:
            #log_ident key in db_managers corresponds to a dbManager object
            
            self.logger.debug("Cleaning up dbManager object for log id %s", log_ident)
            self.log_db_managers[log_ident].cleanup() #run the cleanup method, which ends the update thread. everything else is garbage collected
            
            self.logger.debug("Removing dbManager object for log id %s", log_ident)
            del self.log_db_managers[log_ident]
    
    def sendLogUpdates(self):
        if len(self.log_clients) == 0:
            self.logger.info("sendLogUpdates: No clients connected")

            return
        
        self.logger.debug("%d: Sending updates. Number of clients: %d", int(round(time.time())), len(self.log_clients))
        for log_id in self.log_ordered_clients:
            if log_id != "none":
                #the key will correspond to a set of client objects which are listening for updates on this log id
                
                for client in self.log_ordered_clients[log_id]:
                    if client: #make sure the client still exists
                        #client is a websocket client object, which data can be sent to using client.write_message, etc
                        #client.write_message("HELLO!")
                        self.logger.debug("Checking for updates for client %s on id %s", client, log_id)
                        if log_id in self.log_db_managers:
                            if not client.HAD_FIRST_UPDATE:
                            #need to send complete values on first update to keep clients in sync with the server
                                #if we have data yet
                                if self.log_db_managers[log_id]._stat_complete_table and self.log_db_managers[log_id]._score_table:
                                    #send a complete update to the client
                                    client.write_message(self.log_db_managers[log_id].firstUpdate())
                                    
                                    client.HAD_FIRST_UPDATE = True
                                
                            else:
                                delta_update_dict = self.log_db_managers[log_id].compressedUpdate()
                                self.logger.debug("Got update dict for %s", log_id)
                                if delta_update_dict: #if the dict is not empty, send it. else, just keep processing and waiting for new update
                                    self.logger.debug("Sending update to client %s", client)
                                    client.write_message(delta_update_dict)
    
    def _sendUpdateThread(self, event):
        #this method is run in a thread, and acts as a timer
        while not event.is_set():
            event.wait(self.update_rate)

            self.sendLogUpdates()

    def _logFinishedCallback(self, log_ident):
        self.logger.info("Log id %s is over. Closing connections", log_ident)
        if log_ident in self.log_ordered_clients:
            for client in self.log_ordered_clients[log_ident]:
                client.write_message("LOG_END")
                
                client.close() #on_close will take care of empty sets and what not!
                
                self.delDBManager(log_ident)

class webtvRelayHandler(tornado.websocket.WebSocketHandler):
    pass
        
class logUpdateHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        self.LOG_IDENT_RECEIVED = False
        self.LOG_IDENT = None
        
        self.HAD_FIRST_UPDATE = False
        
        tornado.websocket.WebSocketHandler.__init__(self, application, request, **kwargs)
    
    def open(self):
        #client connects
        """
        This is a bit confusing. We add the client object to a set of objects, so it can later be accessed to send messages (and the connection will be maintained).
        All class variables (clients, log_idents, cache, etc) are required to be global accross the objects, so we add it to a set in the application class, which all logUpdateHandler objects inherit
        
        Hence, if we have a function that iterates over the client set, we can access each client's connection object and send messages
        
        A new object is created for every new client
        """
        
        #inherits object "request" (which is a HTTPRequest object defined in tornado.httpserver) from tornado.web.RequestHandler
        self.application.logger.info("Client connected. IP: %s", self.request.remote_ip)
        
        self.application.log_clients.add(self)
        self.application.log_ordered_clients["none"].add(self)
        
    def on_close(self):
        #client disconnects
        self.application.logger.info("Client disconnected. IP: %s", self.request.remote_ip)
        self.application.log_clients.remove(self)

        self.application.removeFromOrderedClients(self)
        
        return
        
    def on_message(self, msg):
        #client will send the log ident upon successful connection
        self.application.logger.info("Client %s sent msg: %s", self.request.remote_ip, msg)
        
        if (self.LOG_IDENT_RECEIVED):
            self.application.logger.debug("Client %s has already sent log ident \"%s\"", self.request.remote_ip, self.LOG_IDENT)
            return
        
        #a standard message will be a json encoded message with key "ident"
        #i.e [ "ident" : 2315363_121212_1234567]
        try:
            parsed_msg = tornado.escape.json_decode(msg) 
            
        except ValueError:
            self.application.logger.exception("ValueError trying to decode message")
            
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
        
        self.application.logger.debug("Received log ident '%s'. Checking cache", log_id)
        
        #now we check if the log id exists, and if the game is still live
        #first, check the cache. invalid log idents will never be in the cache
        for cache_info in self.application.log_cache:
            #cache_info = (cache_time, log_ident, status<t/f>)
            #check for ident first
            self.application.logger.debug("Cache info: %s", cache_info)
            
            if cache_info[1] == log_id:
                self.application.logger.debug("Log ident is in the cache. Checking live status")
                log_cached = True
                
                #was the log live @ last cache? (logs will never go live again after ending)
                if (cache_info[2] == True):
                    #need to check if the cache is outdated
                    time_ctime = int(round(time.time()))
                    self.application.logger.debug("Log id %s is cached as live", log_id)
                    
                    if ((time_ctime - cache_info[0]) > 60): #20 seconds have passed since last log check, so we need to refresh the cache
                        self.application.logger.debug("Cache has expired for log id %s. Refreshing status", log_id)
                        
                        self.application.removeFromCache(cache_info)
                        
                        self.getLogStatus(log_id)
                            
                    else:
                        #cached status is accurate enough
                        #add the client to the ordered_clients dict with correct log ident
                        self.application.logger.debug("Cache for %s is recent. Using cached status", log_id)
                        
                        self.write_message("LOG_IS_LIVE") #notify client the log is live
                        
                        self.application.addDBManager(log_id) #self.application.db, self.application.update_rate
                        self.application.addToOrderedClients(log_id, self)
                        
                else:
                    #notify client the log is inactive, and close connection
                    
                    #TODO: Add something to prevent repeat invalid connections from same IP
                    
                    self.application.logger.debug("Log id %s is not live. Closing connection", log_id)
                    
                    self.write_message("LOG_NOT_LIVE")
                    self.close()
                
                break
        
        #couldn't find the log in the cache, so it's either fresh or invalid
        if not log_cached:
            self.application.logger.debug("Log id %s is not cached. Getting status", log_id)
            self.getLogStatus(log_id) #getLogStatus adds the ident to the cache if it is valid

    def getLogStatus(self, log_ident):
        """
        Executes the query to obtain the log status
        """
        
        i = 0
        for conn in self.application.db._pool:
            if not conn.busy():
                i += 1
        
        self.application.logger.info("Number of non-busy pSQL conns @ getLogStatus: %d", i)
        

        #psycopg2 will automatically escape the string parameter, so we don't need to worry about sanity checking it for injections
        try:
            self.application.db.execute("SELECT live FROM livelogs_servers WHERE log_ident = %s", (log_ident,), callback=self._logStatusCallback)

        except:
            self.application.logger.exception("Exception occurred while trying to get log status")

            #we should call getlogstatus again, because we need to get the log's status and it is most likely just an operational error
            self.getLogStatus(log_ident)

    
    @tornado.web.asynchronous
    def _logStatusCallback(self, cursor, error):
        if error:
            self.write_message("LOG_ERROR")
            self.application.logger.error("Error querying database for log status")
            
            self.close()
            return
        
        #if live is NOT NULL, then the log exists
        #live == t means the log is live, and live == f means it's not live
        
        results = cursor.fetchone() #fetchone returns a list, we _should_ only have 1 element and it'll be the first (idx 0)
        
        if results and len(results) > 0:
            live = results[0]
        
            if live == True:
                #add the client to the ordered_clients dict with correct log ident
                self.application.logger.debug("Log %s is live on refreshed status", self.LOG_IDENT)
                if self:
                    self.write_message("LOG_IS_LIVE") #notify client the log is live
                    
                    self.application.addToCache(self.LOG_IDENT, True)
                    self.application.addDBManager(self.LOG_IDENT, self.application.db, self.application.update_rate)
                    self.application.addToOrderedClients(self.LOG_IDENT, self)
                
            elif live == False:
                self.application.logger.debug("Log %s is not live", self.LOG_IDENT)
                self.application.addToCache(self.LOG_IDENT, False)
                
                self.closeLogUpdate()
                
            else:
                self.closeLogUpdate()
        else:
            self.closeLogUpdate()
                
    def closeLogUpdate(self):
        if self:
            self.write_message("LOG_NOT_LIVE")
        
            self.close()
            
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
    logger.setLevel(logging.DEBUG)
    logger.addHandler(log_file_handler)

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
        