import tornado.ioloop
import tornado.web
import tornado.auth

import tornado.options
from tornado.options import define, options

import os.path

define("port", default=8000, help="Which port to run this server on", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/log/([^/]+)", LogHandler),
        ]

        settings = dict(
            cookie_secret = "SECRET_COOKIE_LOLOLOL121345436836",
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies = True,
            autoescape = "xhtml_escape",
        )

        tornado.web.Application.__init__(self, handlers, **settings)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html")

class LogHandler(tornado.web.RequestHandler):
    def get(self, log_num):
        self.write("heuheu")

if __name__ == "__main__":
    application.listen(8011)
    tornado.ioloop.IOLoop.instance().start()
