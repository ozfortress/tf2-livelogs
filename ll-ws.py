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
    #inherits request (which is a HTTPRequest object defined in tornado.httpserver) from tornado.web.RequestHandler

    clients = set()
    log_idents = set()
    cache = []
    cache_size = 200
    
    logger = logging.getLogger("LIVE LOG UPDATE")
    
    #def allow_draft76(self):
    #    return True
        
    def open(self):
        #client connects
        """
        This is a bit confusing. We add the client object to a set of objects, so it can later be accessed to send messages (and the connection will be maintained).
        All class variables (clients, log_idents, cache, etc) are required to be global accross the objects (same memory address), so we add it to the classes' set, which all clients inherit
        
        Hence, if we have a function that iterates over the client set, we can access each client's connection object and send messages
        
        A new object is created for every new client
        """
        
        logger.info("Client connected. IP: %s", self.request.remote_ip)
        
        logUpdateHandler.clients.add(self)
        
    def on_close(self):
        #client disconnects
        logger.info("Client disconnected. IP: %s", self.request.remote_ip)
        logUpdateHandler.clients.remove(self)
        
    def on_message(self, msg):
        #client will send the log ident upon successful connection
        logger.info("Client %s sent msg: %s", self.request.remote_ip, msg)
        
        #a standard message will be a json encoded message, with key ident, and the value of the log ident
        parsed_msg = tornado.escape.json_decode(msg) 
        
        log_id = parsed_msg["ident"]
        
        #now we check if the log id exists, and if the game is still live
        #"SELECT live FROM livelogs_servers WHERE log_ident = %s" % log_id
        #if live is NOT NULL, then the log exists
        #live == t means the log is live, and live == f means it's not live
        
        
        
    