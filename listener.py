import SocketServer
import parser
import threading

class llListenerHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip()
        sock = self.request[1]

        print "LOG: %s" % data


class llListener(SocketServer.UDPServer):
    def __init__(self, listener_address, handler_class=llListenerHandler):
        SocketServer.UDPServer.__init__(self, listener_address, handler_class)
        print "Initialized log listener"
        return

    def server_close(self):
        print "Listener exiting"

class llListenerObject():
    def __init__(self, listenIP, lClientAddr):
        self.listenIP = listenIP

        self.listenAddress = (self.listenIP, 0)
        self.listener = llListener(self.listenAddress, llListenerHandler)

        self.lip, self.lport = self.listener.server_address

        self.lClientAddr = lClientAddr

        #self.lThread = threading.Thread(target=self.listener.serve_forever)
        #self.lThread.setDaemon(True)
        #self.lThread.start()

    def startListening(self):
        self.listener.serve_forever()