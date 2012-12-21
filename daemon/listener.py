import SocketServer
import threading
import time
import socket
import struct
from pprint import pprint

import parser

class llListenerHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request[0].strip()
        sock = self.request[1]

        #print "LOG: %s" % data
        if not self.server.parser.HAD_ERROR:
            self.server.parser.parse(data)


class llListener(SocketServer.UDPServer):
    def __init__(self, listener_address, timeout, handler_class=llListenerHandler):
        SocketServer.UDPServer.__init__(self, listener_address, handler_class)
        print "Initialised log listener. Waiting for logs"

        self.timeout = timeout

        self.timeoutTimer = threading.Timer(timeout, self.handle_server_timeout)
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
            self.timeoutTimer = threading.Timer(self.timeout, self.handle_server_timeout)
            self.timeoutTimer.start()

            return True
        else:
            #print "Client address differs from initial client. Rejecting log"
            return False
    
    def handle_server_timeout(self, game_over=False):
        if game_over:
            print "Game over. Closing listening socket"
            #put the shutdown in a timer to prevent a race condition
            
            self.timeoutTimer.cancel()
            
            self.gameOverTimer = threading.Timer(5.0, self.shutdown)
            self.gameOverTimer.start()
            
            
        else:
            print "Server timeout (no logs received in 90 seconds). Exiting"
            
            #toggle log's status and stop recording
            if not self.parser.HAD_ERROR:
                self.parser.endLogParsing()
            
            self.shutdown()
       
        return



class llListenerObject():
    def __init__(self, listenIP, lClientAddr, current_map, log_name, webtv_port=None, timeout=90.0):
        self.listenIP = listenIP

        self.listenAddress = (self.listenIP, 0)
        self.listener = llListener(self.listenAddress, timeout, handler_class=llListenerHandler)

        print "Initialising parser"
        
        self.unique_parser_ident = str(self.ip2long(lClientAddr[0])) + "_" + str(lClientAddr[1]) + "_" + str(int(round(time.time())))
        
        self.listener.parser = parser.parserClass(self.unique_parser_ident, server_address = lClientAddr, current_map = current_map, log_name = log_name, endfunc = self.listener.handle_server_timeout, webtv_port = webtv_port)
        
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

    def ip2long(self, ip):
        return struct.unpack('!L', socket.inet_aton(ip))[0]

    def error_cleanup(self):
        self.listener.timeoutTimer.cancel()
        self.listener.shutdown()