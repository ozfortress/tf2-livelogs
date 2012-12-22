"""
Websocket stuff, for dynamic updating of stats and sourcetv 2d relay

"""

import tornado
import tornado.options
import tornado.websocket
import tornado.web
import tornado.ioloop
import tornado.escape
from tornado import gen

import logging
import time
import threading
import momoko
import ConfigParser

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
    #inherits object "request" (which is a HTTPRequest object defined in tornado.httpserver) from tornado.web.RequestHandler

    clients = set() #set of ALL connected clients
    ordered_clients = { "none" : set() } #ordered clients dict will have data in the form of: [ "log ident": (client, client, client) ], where the clients are in a set corresponding to
                                         #the log ident sent by the client. new clients are added to "none" upon connection, and moved when a log ident is received
    
    cache = [] #holds a set of tuples containing log idents, the last time they were updated, and the status (live/not live) | [(cache_time, log_ident, status<t/f>), (cache_time, log_ident, status<t/f>)]
    cache_size = 200 #max number of logs holdable
    
    logger = logging.getLogger("CLIENTUPDATE")
    
    #def allow_draft76(self):
        #allow old versions of the websocket protocol, for legacy support. LESS SECURE
    #    return True
    def __init__(self, application, request, **kwargs):
        self.LOG_IDENT_RECEIVED = False
        self.LOG_IDENT = None
        
        tornado.websocket.WebSocketHandler.__init__(self, application, request, **kwargs)
    
    def open(self):
        #client connects
        """
        This is a bit confusing. We add the client object to a set of objects, so it can later be accessed to send messages (and the connection will be maintained).
        All class variables (clients, log_idents, cache, etc) are required to be global accross the objects, so we add it to the classes' set, which all clients inherit
        
        Hence, if we have a function that iterates over the client set, we can access each client's connection object and send messages
        
        A new object is created for every new client
        """
        
        logger.info("Client connected. IP: %s", self.request.remote_ip)
        
        logUpdateHandler.clients.add(self)
        logUpdateHandler.ordered_clients["none"].add(self)
        
        print "Clients without ID:"
        print logUpdateHandler.ordered_clients["none"]
        
    def on_close(self):
        #client disconnects
        logger.info("Client disconnected. IP: %s", self.request.remote_ip)
        logUpdateHandler.clients.remove(self)
        
        if self in logUpdateHandler.ordered_clients["none"]: #if client hasn't sent a log ident yet, and connection closes remove the object
            logUpdateHandler.ordered_clients["none"].remove(self) 
        else: #client has sent log ident and been assigned. need to search for the object
            for key, set in logUpdateHandler.ordered_clients:
                if self in set:
                    set.remove(self)
                    if len(set) == 0:
                        del logUpdateHandler.ordered_clients[key]
                        
                        break
                        
        return
        
    def on_message(self, msg):
        #client will send the log ident upon successful connection
        logger.info("Client %s sent msg: %s", self.request.remote_ip, msg)
        
        if (self.LOG_IDENT_RECEIVED):
            logger.info("Client %s has already sent log ident \"%s\"", self.request.remote_ip, self.LOG_IDENT)
            return
        
        #a standard message will be a json encoded message, with key "ident", and the value of the log ident i.e [ "ident" : 2315363_121212_1234567 ]
        try:
            parsed_msg = tornado.escape.json_decode(msg) 
            
        except ValueError:
            logger.info("ValueError trying to decode message")
            
            logUpdateHandler.clients.removed(self)
            logUpdateHandler.ordered_clients["none"].discard(self)
            return
            
        log_id = parsed_msg["ident"]
        if not log_id:
            #invalid message received. IGNORE
            return
            
        log_cached = False
        
        self.LOG_IDENT_RECEIVED = True
        self.LOG_IDENT = log_id
        
        logger.info("Received log ident '%s'", log_id)
        
        #now we check if the log id exists, and if the game is still live
        #first, check the cache. invalid log idents will never be in the cache
        for cache_info in logUpdateHandler.cache:
            #cache_info = (cache_time, log_ident, status<t/f>)
            #check for ident first
            
            if cache_info[1] == log_id:
                logger.info("Log ident is in the cache")
                log_cached = True
                #was the log live @ last cache? (logs will never go live again after ending)
                
                if (cache_info[2] == True):
                    #need to check if the cache is outdated
                    time_ctime = int(round(time.time()))
                    logger.info("Log is cached as live")
                    
                    if ((time_ctime - cache_info[0]) > 20): #20 seconds have passed since last log check, so we need to refresh the cache
                        logger.info("Cache has expired. Getting status")
                        self.getLogStatus(log_id)
                            
                    else:
                        #cached status is accurate enough
                        #add the client to the ordered_clients dict with correct log ident
                        self.write_message("LOG_IS_LIVE") #notify client the log is live
                        
                        logUpdateHandler.addToOrderedClients(log_id, self)
                        
                else:
                    #notify client the log is inactive, and close connection
                    
                    #TODO: Add something to prevent repeat connections from same IP
                    self.write_message("LOG_NOT_LIVE")
                    self.close()
                
                break
        
        #couldn't find the log in the cache, so it's either fresh or invalid
        if not log_cached:
            self.getLogStatus(log_id) #getLogStatus adds the ident to the cache if it is valid
        
    def validClient(self):
        pass
        
    @classmethod
    def addToOrderedClients(cls, log_id, client):
        if cls.ordered_clients[log_id]:
            #log_id key exists, just need client to add to set
            cls.ordered_clients[log_id].add(client)
            
        else:
            #key doesn't exist with a set, so create the set and add the client to it
            cls.ordered_clients[log_id] = set()
            cls.ordered_clients[log_id].add(client)
            
        cls.ordered_clients["none"].discard(client) #remove from unallocated set
        
    @classmethod
    def removeFromOrderedClients(cls, client):
        pass
        
    @classmethod    
    def addToCache(cls, log_ident, status):
        #cache_info = (cache_time, log_ident, status<t/f>)
        cls.cache.append((int(round(time.time())), log_ident, status))
        
    @classmethod
    def removeFromCache(cls, log_ident):
        pass
    
    def getLogStatus(self, log_ident):
        """
        Gets the status of a log ident, and if the log is valid adds it to the cache
        
        @return True if log is live and valid. False if log is not live or is invalid
        
        """
        
        #"SELECT live FROM livelogs_servers WHERE log_ident = %s" % log_id
        #if live is NOT NULL, then the log exists
        #live == t means the log is live, and live == f means it's not live
        
        res_cursor = self.application.db.execute("SELECT live FROM livelogs_servers WHERE log_ident = E'%s'", (log_ident,), callback=_logStatusCallback)
        
        """
        This is now done in _statusCallback
        live = res_cursor.fetchone()
        if live == "t":
            logUpdateHandler.addToCache(log_ident, True)
            return True
            
        elif live == "f":
            logUpdateHandler.addToCache(log_ident, False)
            return False
            
        else:
            return 
        """
    
    def _logStatusCallback(self, cursor, error):
        if error:
            self.write_message("LOG_ERROR")
            logger.info("Error querying database for log status")
        
        live = cursor.fetchone()
        
        if live == "t":
            #add the client to the ordered_clients dict with correct log ident
            logger.info("Log is live on refreshed status")
            self.write_message("LOG_IS_LIVE") #notify client the log is live
            
            logUpdateHandler.addToCache(self.LOG_IDENT, True)
            logUpdateHandler.addToOrderedClients(self.LOG_IDENT, self)
            
        elif live == "f":

            self.write_message("LOG_NOT_LIVE")
            
            logger.info("Log is no longer live")
            
            logUpdateHandler.addToCache(self.LOG_IDENT, False)
            
            self.close()
                            
        else:                    
            #invalid log ident
            logger.info("Invalid log ident specified (live is null)")
            self.write_message("LOG_NOT_LIVE")
            
        
    @classmethod
    def singleMomokoQuery(self, query):
        pass
    
    @classmethod
    def sendLogUpdates(cls):
        pass
        
        
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
    
    
    llWebSocketServer.listen(tornado.options.options.port, tornado.options.options.ip)
    logger.info("Successfully listening on %s:%s", tornado.options.options.ip, tornado.options.options.port)
    
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().stop()
        logger.info("Keyboard interrupt. Exiting")
        