import tornado
import tornado.options
import tornado.websocket
import tornado.web
import tornado.ioloop

import logging

tornado.options.define("port", default=61224, help="Port the websocket server will run on", type=int)

class llWSApplication(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/logupdate", liveUpdateHandler),
            (r"/webrelay", webtvRelayHandler),
        ]
        
        settings = dict(
            cookie_secret = "12345",
        )
        
        tornado.web.Applcation.__init__(self, handlers, **settings)
        
class liveUpdateHandler(tornado.websocket.WebSocketHandler):
    clients = set()
    log_idents = set()
    cache = []
    cache_size = 200
    
    def allow_draft76(self):
        return True
        
    def open(self):
        self.waiters.add(self)
        
    def on_close(self):
        s