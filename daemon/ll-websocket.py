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

from livelib import dbmanager.dbManager

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
    def __init__(self, update_rate=10):
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

        self.update_rate = update_rate
        
        self.log_clients = set() #set of ALL connected clients
        self.log_ordered_clients = { "none": set() } #ordered clients dict will have data in the form of: [ "log ident": (client, client, client) ], where the clients are in a set corresponding to
                                                #the log ident sent by the client. new clients are added to "none" upon connection, and moved when a log ident is received
        self.log_db_managers = {} #a dictionary containing dbManager objects corresponding to log ids

        self.log_cache = [] #holds a set of tuples containing log idents, the last time they were updated, and the status (live/not live) | [(cache_time, log_ident, status<t/f>), (cache_time, log_ident, status<t/f>)]

        self.log_update_thread_event = threading.Event()
        self.log_update_thread = threading.Thread(target = self._sendUpdateThread, args=(self.log_update_thread_event,))
        self.log_update_thread.daemon = True

        self.log_update_thread.start()

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
                if log_id in self.log_db_managers:
                    log_manager = self.log_db_managers[log_id]

                    delta_update_dict = log_manager.compressedUpdate()
                    self.logger.debug("Got update dict for %s: %s", log_id, delta_update_dict)

                    full_update_dict = {}

                    for client in self.log_ordered_clients[log_id]:
                        #client is a websocket client object, which data can be sent to using client.write_message, etc
                        #client.write_message("HELLO!")
                        if not client.HAD_FIRST_UPDATE:
                            #need to send complete values on first update to keep clients in sync with the server
                            #if we have data yet

                            if not full_update_dict:
                                if log_manager._stat_complete_table and log_manager._score_table:

                                    full_update_dict = log_manager.firstUpdate()

                            if full_update_dict:
                                #send a complete update to the client
                                client.write_message(full_update_dict)
                            
                                client.HAD_FIRST_UPDATE = True
                        else:
                            if delta_update_dict: #if the dict is not empty, send it. else, just keep processing and waiting for new update
                                self.logger.debug("Sending update to client %s", client.cip)
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

    def add_client(self, client_obj):


    def delete_client(self, client_obj):


class webtvRelayHandler(tornado.websocket.WebSocketHandler):
    pass
        
class logUpdateHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        self._log_ident_received = False
        self._log_ident = None

        self.__valid_log_received = False
        
        self.HAD_FIRST_UPDATE = False
        
        tornado.websocket.WebSocketHandler.__init__(self, application, request, **kwargs)
    
    def open(self):
        #client connects
        #inherits object "request" (which is a HTTPRequest object defined in tornado.httpserver) from tornado.web.RequestHandler

        self.application.logger.info("Client connected. IP: %s", self.request.remote_ip)

        self.cip = self.request.remote_ip
        
    def on_close(self):
        #client disconnects
        self.application.logger.info("Client disconnected. IP: %s", self.request.remote_ip)

        self.application.delete_client(self)
        
        return
        
    def on_message(self, msg):
        #client will send the log ident upon successful connection
        self.application.logger.info("Client %s sent msg: %s", self.request.remote_ip, msg)

        if (self._log_ident_received):
            self.application.logger.debug("Client %s has already sent log ident \"%s\"", self.request.remote_ip, self._log_ident)
            return
        
        #a standard message will be a json encoded message with key "ident"
        #i.e [ "ident" : 2315363_121212_1234567]
        try:
            parsed_msg = tornado.escape.json_decode(msg) 
            
        except ValueError:
            self.application.logger.exception("ValueError trying to decode message")
            
            self.close()
            
            return
            
        log_ident = str(parsed_msg["ident"])
        if not log_ident:
            #invalid message received, disconnect this bitch

            self.close()

            return
        
        self._log_ident_received = True
        self._log_ident = log_ident
        
        self.application.logger.debug("Received log ident '%s'. Checking cache", log_ident)
        
        #now we check if the log id exists, and if the game is still live
        #first, check the cache. invalid log idents will never be in the cache

        log_cache = self.get_log_cache(log_ident)
        if log_cache:
            #log is cached
            if log_cache[2] == True:
                self.application.add_client(self, log_ident)
                self.write("LOG_IS_LIVE")

            else:
                self.write("LOG_NOT_LIVE")
                self.close()

        else:
            #couldn't find the log in the cache, so it's either fresh or invalid
            self.application.logger.debug("Log id %s is not cached. Getting status", log_ident)
            self.get_log_status(log_ident) #getLogStatus adds the ident to the cache if it is valid

    def get_log_cache(self, log_ident):
        #return a cache only if the cache is valid

        for log_cache in self.application.log_cache:
            #cache_info = (cache_time, log_ident, status<t/f>)
            if log_cache[1] == log_ident:
                time_ctime = int(round(time.time()))
                if (time_ctime - log_cache[0]) > 60:
                    #cache is expired
                    self.application.remove_from_cache(log_cache)
                    break

                else:
                    return log_cache

        return None


    def get_log_status(self, log_ident):
        """
        Executes the query to obtain the log status
        """

        #psycopg2 will automatically escape the string parameter, so we don't need to worry about sanity checking it for injections
        try:
            self.application.db.execute("SELECT live FROM livelogs_servers WHERE log_ident = %s", (log_ident,), callback=self._status_callback)

        except:
            self.application.logger.exception("Exception occurred while trying to get log status")

            #we should call getlogstatus again, because we need to get the log's status and it is most likely just an operational error
            self.get_log_status(log_ident)

    
    @tornado.web.asynchronous
    def _status_callback(self, cursor, error):
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
                self.application.logger.debug("Log %s is live on refreshed status", self._log_ident)
                if self:
                    self.write_message("LOG_IS_LIVE") #notify client the log is live
                    
                    self.application.addToCache(self._log_ident, True)
                    self.application.addDBManager(self._log_ident, self.application.db, self.application.update_rate)
                    self.application.addToOrderedClients(self._log_ident, self)
                
            elif live == False:
                self.application.logger.debug("Log %s is not live", self._log_ident)
                self.application.addToCache(self._log_ident, False)
                
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
    
    llWebSocketServer = llWSApplication(update_rate = tornado.options.options.update_rate)
        
    llWebSocketServer.db = momoko.Pool(
            dsn = db_details,
            minconn = 1, #minimum number of connections for the momoko pool to maintain
            maxconn = 4, #max number of conns that will be opened
            cleanup_timeout = 10, #how often (in seconds) connections are closed (cleaned up) when number of connections > minconn
        )
    
    llWebSocketServer.listen(tornado.options.options.port, tornado.options.options.ip)
    logger.info("Websocket server listening on %s:%s", tornado.options.options.ip, tornado.options.options.port)
    
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        llWebSocketServer.db.close()
        tornado.ioloop.IOLoop.instance().stop()
        logger.info("Keyboard interrupt. Exiting")
        