"""
Websocket stuff, for dynamic updating of stats and sourcetv 2d relay

"""

import tornado
import tornado.options
import tornado.websocket
import tornado.web
import tornado.ioloop
import tornado.escape

import logging
import time
import threading

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

tornado.options.define("port", default=61224, help="Port the websocket server will run on", type=int)

class llWSApplication(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/logupdate", logUpdateHandler),
            (r"/webrelay", webtvRelayHandler),
        ]
        
        settings = dict(
            cookie_secret = "12345",
        )
        
        tornado.web.Applcation.__init__(self, handlers, **settings)
        
class logUpdateHandler(tornado.websocket.WebSocketHandler):
    #inherits object "request" (which is a HTTPRequest object defined in tornado.httpserver) from tornado.web.RequestHandler

    clients = set() #set of ALL connected clients
    ordered_clients = { "none" : set() } #ordered clients dict will have data in the form of: [ "log ident": (client, client, client) ], where the clients are in a set corresponding to
                                         #the log ident sent by the client. new clients are added to "none" upon connection, and moved when a log ident is received
    
    cache = [] #holds a set of tuples containing log idents, the last time they were updated, and the status (live/not live) | [(cache_time, log_ident, status<t/f>), (cache_time, log_ident, status<t/f>)]
    cache_size = 200 #max number of logs holdable
    
    logger = logging.getLogger("LIVE LOG UPDATE")
    
    #def allow_draft76(self):
        #allow old versions of the websocket protocol, for legacy support. LESS SECURE
    #    return True
        
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
        parsed_msg = tornado.escape.json_decode(msg) 
        
        log_id = parsed_msg["ident"]
        if not log_id:
            #invalid message received. IGNORE
            return
            
        log_cached = False
        
        self.LOG_IDENT_RECEIVED = True
        self.LOG_IDENT = log_id
        
        #now we check if the log id exists, and if the game is still live
        #first, check the cache. invalid log idents will never be in the cache
        for cache_info in cache:
            #cache_info = (cache_time, log_ident, status<t/f>)
            #check for ident first
            if cache_info[1] == log_id:
                log_cached = True
                #was the log live @ last cache? (logs will never go live again after ending)
                if (cache_info[2] == True):
                    #need to check if the cache is outdated
                    time_ctime = int(round(time.time()))
                    
                    if ((time_ctime - cache_info[0]) > 20): #20 seconds have passed since last log check, so we need to refresh the cache
                        live = logUpdateHandler.getLogStatus(log_id)
                        if (live):
                            #add the client to the ordered_clients dict with correct log ident
                            self.write_message("LOG_IS_LIVE") #notify client the log is live
                            
                            logUpdateHandler.addToOrderedClients(log_id, self)
                        else:
                            self.write_message("LOG_NOT_LIVE")
                            self.close()
                            
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
            live = logUpdateHandler.getLogStatus(log_id) #getLogStatus adds the ident to the cache if it is valid
            if (live):
                #add the client to the ordered_clients dict with correct log ident
                self.write_message("LOG_IS_LIVE") #notify client the log is live
                
                logUpdateHandler.addToOrderedClients(log_id, self)
            else:
                self.write_message("LOG_NOT_LIVE")
                self.close()
            
        
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
    def addToCache(cls, log_ident):
        pass
        
    @classmethod
    def removeFromCache(cls, log_ident):
        pass
    
    @classmethod
    def getLogStatus(cls, log_ident):
        """
        Gets the status of a log ident, and if the log is valid adds it to the cache
        
        @return True if log is live and valid. False if log is not live or is invalid
        
        
        
        """
        #"SELECT live FROM livelogs_servers WHERE log_ident = %s" % log_id
        #if live is NOT NULL, then the log exists
        #live == t means the log is live, and live == f means it's not live
        
        #add to cache (or update cache)
        pass
        
    @classmethod
    def sendLogUpdates(cls):
        pass
        
        
if __name__ == '__main__':
    tornado.options.parse_command_line()
    
    llWebSocketServer = llWSApplication():
    
    llWebSocketServer.listen(options.port)
    
    tornado.ioloop.IOLoop.instance().start()