import SocketServer
import threading
import time
import socket
import struct
import logging
from pprint import pprint

import parser

class llListenerHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        data = self.request[0].strip()
        sock = self.request[1]

        if self.server.parser and not self.server.parser.HAD_ERROR:
            self.server.parser.parse(data)


class llListener(SocketServer.UDPServer):
    def __init__(self, logger, listener_address, timeout, listener_object, handler_class=llListenerHandler):
        self.logger = logger
        self.logger.info("Initialised log listener. Waiting for logs")
        self.parser = None
        self.timeout = timeout

        self.timeoutTimer = threading.Timer(timeout, self.handle_server_timeout)
        self.timeoutTimer.start()

        self.listener_object = listener_object #llListenerObject address, which holds this listener. needed to end the listening thread, and remove the object from the daemon's set

        self.timeoutTimer = threading.Timer(self.timeout, self.handle_server_timeout)

        SocketServer.UDPServer.__init__(self, listener_address, handler_class)

    def verify_request(self, request, client_address):
        """
        Verify the request to make sure it's coming from the expected client
        Likely won't be from the same port every time, so we'll just check by IP
        """
        #print "Current client addr: " + client_address[0] + ". Expected addr: " + self.client_address[0]

        #logging.debug("Request: %s", request)

        if (client_address[0] == self.client_server_address[0]):
            #print "Client address is same as initial client. Accepting log"
            #reset the timeout timer
            self.timeoutTimer.cancel()

            #restart the timeout timer, so it doesn't prematurely timeout the listener
            self.timeoutTimer.start()

            return True
        else:
            #print "Client address differs from initial client. Rejecting log"
            return False
    
    def handle_server_timeout(self, game_over=False):
        if game_over:
            self.logger.info("Game over. Closing listening socket")
            
            self.timeoutTimer.cancel()
            
            time.sleep(1) #sleep for 1 second to prevent a race condition
            self.shutdown()
            
        else:
            if not self.parser.LOG_PARSING_ENDED:
                self.logger.info("Server timeout (no logs received in %0.2f seconds). Exiting", self.timeout)
                
                #toggle log's status and stop recording
                if not self.parser.HAD_ERROR:
                    self.parser.endLogParsing()
                
                self.shutdown()
       
        return

    def shutdown(self):
        self.logger.info("Shutting down listener on %s:%s", self.server_address[0], self.server_address[1])

        #need to close the parser's database connection
        if self.parser.db:
            if not self.parser.db.closed: #cancel current operations and end the log
                #self.parser.db.cancel()
                self.parser.endLogParsing()
                  
        SocketServer.UDPServer.shutdown(self)
        
        #should no longer be listening or anything now, so we can call close_object, which will join the thread and remove llListenerObject from the daemon's set
        self.listener_object.close_object()

class llListenerObject(object):
    def __init__(self, client_api_key, listen_ip, client_address, current_map, log_name, end_function, webtv_port=None, timeout=90.0):
        self.unique_parser_ident = "%s_%s_%s" % (self.ip2long(client_address[0]), client_address[1], int(round(time.time())))

        self.logger = logging.getLogger("LISTENER #%s" % self.unique_parser_ident)
        self.logger.setLevel(logging.DEBUG)

        self.listen_ip = listen_ip

        self.listenAddress = (self.listen_ip, 0)
        self.listener = llListener(self.logger, self.listenAddress, timeout, self, handler_class=llListenerHandler)

        self.logger.info("Initialising parser. Log name: %s, Map: %s, WebTV port: %s", log_name, current_map, webtv_port)
        
        self.listener.parser = parser.parserClass(self.unique_parser_ident, server_address = client_address, current_map = current_map, log_name = log_name, endfunc = self.listener.handle_server_timeout, webtv_port = webtv_port)
        
        self.listener.client_server_address = client_address #tuple containing the client's server IP and PORT
        self.listener.client_api_key = client_api_key
        
        self.lip, self.lport = self.listener.server_address #get the listener's address, so it can be sent to the client

        self.client_address = client_address
        
        self.end_function = end_function

    def startListening(self):
        #start serving in a thread. the object will be stored in a set owned by the daemon object, so the thread will be kept alive
        self.lthread = threading.Thread(target = self.listener.serve_forever)
        self.lthread.daemon = True
        self.lthread.start()
        
    def returnClientAddress(self):
        return self.client_address

    def ip2long(self, ip):
        return struct.unpack('!L', socket.inet_aton(ip))[0]

    def had_error(self):
        if self.listener.parser is not None:
            return self.listener.parser.HAD_ERROR
        else:
            return True

    def error_cleanup(self):
        self.listener.timeoutTimer.cancel()
        self.listener.shutdown()
        
    def close_object(self): #only ever called by listener.shutdown()
        while self.lthread.isAlive(): #attempt to join the thread
            self.lthread.join(5)
        
        self.logger.info("Listener thread joined. Removing listener object from set")
        
        self.end_function(self) #self is the same as the newListen object added by the daemon
