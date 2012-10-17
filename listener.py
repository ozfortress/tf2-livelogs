import SocketServer
import threading
import time
from pprint import pprint

import parser

class llListenerHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request[0].strip()
        sock = self.request[1]

        print "LOG: %s" % data

        #self.server.parser.parse(data)


class llListener(SocketServer.UDPServer):
    def __init__(self, listener_address, handler_class=llListenerHandler):
        SocketServer.UDPServer.__init__(self, listener_address, handler_class)
        print "Initialised log listener. Waiting for logs"

        self.timeoutTimer = threading.Timer(60.0, self.handle_server_timeout)
        self.timeoutTimer.start()

        return

    def verify_request(self, request, client_address):
        """
        Verify the request to make sure it's coming from the expected client
        Won't be from the same port every time, so we'll just check by IP
        """
        #print "Current client addr: " + client_address[0] + ". Expected addr: " + self.lClientAddr[0]
        if (client_address[0] == self.lClientAddr[0]):
            #print "Client address is same as initial client. Accepting log"
            #reset the timeout timer
            self.timeoutTimer.cancel()

            #restart!
            self.timeoutTimer = threading.Timer(60.0, self.handle_server_timeout)
            self.timeoutTimer.start()

            return True
        else:
            #print "Client address differs from initial client. Rejecting log"
            return False
    
    def handle_server_timeout(self):
        print "Server timeout (no logs received in 60 seconds). Exiting"
        self.shutdown()

        return



class llListenerObject():
    def __init__(self, listenIP, lClientAddr, ipgnBooker=None):
        self.listenIP = listenIP

        self.listenAddress = (self.listenIP, 0)
        self.listener = llListener(self.listenAddress, handler_class=llListenerHandler)

        print "Initialising parser"
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
