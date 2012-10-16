import SocketServer
import parser
import threading
from pprint import pprint


class llListenerHandler(SocketServer.BaseRequestHandler):
    #def __init__(self, request, client_address, server):
    #    SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
    #    return

    def handle(self):
        data = self.request[0].strip()
        sock = self.request[1]

        print "LOG: %s" % data

        #self.server.parser.parse(data)


class llListener(SocketServer.UDPServer):
    def __init__(self, listener_address, handler_class=llListenerHandler):
        SocketServer.UDPServer.__init__(self, listener_address, handler_class)
        print "Initialised log listener. Initialising parser instance"

        return

    #def server_close(self):
    #    print "Listener exiting"
    #    return SocketServer.UDPServer.server_close(self)

    #def close_request(self, request_address):
    #    print "Closing log listener request"
    #    return SocketServer.UDPServer.close_request(self, request_address)

class llListenerObject():
    def __init__(self, listenIP, lClientAddr, ipgnBooker=None):
        self.listenIP = listenIP

        self.listenAddress = (self.listenIP, 0)
        self.listener = llListener(self.listenAddress, handler_class=llListenerHandler)

        self.listener.parser = parser.parserClass(lClientAddr, ipgnBooker)
        self.listener.lClientAddr = lClientAddr

        self.lip, self.lport = self.listener.server_address

        self.lClientAddr = lClientAddr

        return

    def startListening(self):
        #lthread = threading.Thread(target=self.listener.serve_forever())
        #lthread.daemon = True
        #lthread.start()
        try:
            self.listener.serve_forever()
        except KeyboardInterrupt:
            self.listener.server_close()

    def returnClientAddress(self):
        return self.lClientAddr
