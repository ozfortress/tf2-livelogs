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
        if self.request[0][-1] == "\0":
            data = self.request[0][:-1].lstrip("\xFF").rstrip() #remove the null byte and strip leading \xFFs and trailing \n
        else:
            #don't need to remove null byte
            data = self.request[0].lstrip("\xFF").rstrip()
            
        #strip leading log information, so logs are written just like a server log
        #we do this by tokenising, getting all tokens after first token and rejoining

        data = "L " + " ".join(data.split(" ")[1:])

        if self.server.parser and not self.server.parser.HAD_ERROR:
            self.server.parser.parse(data)


class llListener(SocketServer.UDPServer):
    def __init__(self, data, handler_class=llListenerHandler):
        self.logger = data.listener_logger
        self.logger.info("Initialised log listener. Waiting for logs")
        self.parser = None

        self.client_secret = data.client_secret

        self._timeout = data.log_timeout

        #self.timeoutTimer = threading.Timer(timeout, self.handle_server_timeout)
        #self.timeoutTimer.start()
        self._using_secret = False

        self.listener_object = data.listener_object #llListenerObject, which holds this listener. needed to end the listening thread, and remove the object from the daemon's set

        self._ended = False
        self._last_message_time = time.time() #set the init time to this, so we can still timeout if nothing is received at all

        SocketServer.UDPServer.__init__(self, data.listener_address, handler_class)

    def verify_request(self, request, client_address):
        """
        Verify the request to make sure it's coming from the expected client
        Check sv_logsecret key, or compare IPs if not using sv_logsecret (or it's broken)
        """
        data = request[0].lstrip("\xFF") #strip leading \xFFs

        if self._using_secret or data[0] == "S":
            #the log is a secret marked log. get the secret out and compare it
            #S23BOB1234L 06/13/2013 - 18:45:22:
            #first token is S<KEY>L

            secret = data.split(" ")[0][1:-1] #get the first token, but only the data between S and L

            if secret == self.client_secret: #secret key matches the client's desired secret
                self._using_secret = True
                self._last_message_time = time.time() # set the epoch value of the time this message was received, for the timeout check

                return True
            else:
                return False

        elif not self._using_secret and data[0] == "R":
            #log is a normal log message
            if client_address[0] == self.client_server_address[0]:
                self._last_message_time = time.time() #the epoch value of the time this message was received, for the timeout check

                return True
            else:
                self.logger.debug("Client address differs from initial client. Rejecting log")
                return False
        
        else:
            self.logger.info("Client sent invalid log message")
            return False
    
    def handle_server_timeout(self, game_over=False):
        if game_over:
            self.logger.info("Game over. Closing listening socket")
            
            self._ended = True #flag log as ended for the cleanup method
            
        else:
            if not self.parser.LOG_PARSING_ENDED:
                self.logger.info("Server timeout (no logs received in %0.2f seconds). Exiting", self._timeout)
                
                #toggle log's status and stop recording
                if not self.parser.HAD_ERROR:
                    self.parser.endLogParsing()
                
                self.__listener_shutdown()
       
        return

    def shutdown_listener(self):
        self.__listener_shutdown()

    def timed_out(self, current_time):
        if (current_time - self._last_message_time) > float(self._timeout): #difference between current time and last message is > the time out. therefore, the listener has timed out
            return True
        else:
            return False

    def __listener_shutdown(self):
        if self.listener_object.lthread and threading.current_thread() is self.listener_object.lthread:
            self.logger.error("__listener_shutdown called from the same thread as the listener. will cause deadlock")

            return

        self.logger.info("Shutting down listener on %s:%s", self.server_address[0], self.server_address[1])

        #need to close the parser's database connection
        if self.parser.db:
            if not self.parser.db.closed: #cancel current operations and end the log
                #self.parser.db.cancel()
                self.parser.endLogParsing()
                  
        self.shutdown() #call the class's in-built shutdown method, which stops listening for new data
        self.server_close() #closes the server socket
        
        #should no longer be listening or anything now, so we can call close_object, which will join the thread and remove llListenerObject from the daemon's set
        self.listener_object.close_object()

class llListenerObject(object):
    def __init__(self, data):
        self.unique_parser_ident = "%s_%s_%s" % (self.ip2long(data.client_address[0]), data.client_address[1], int(round(time.time())))

        self.logger = logging.getLogger("LISTENER #%s" % self.unique_parser_ident)
        self.logger.setLevel(logging.DEBUG)

        self.listen_ip = data.server_ip

        self.listenAddress = (self.listen_ip, 0)

        data.listener_object = self
        data.listener_logger = self.logger
        data.listener_address = self.listenAddress
        data.unique_parser_ident = self.unique_parser_ident

        self.listener = llListener(data, handler_class=llListenerHandler)

        self.logger.info("Initialising parser. Log name: %s, Map: %s, WebTV port: %s", data.log_name, data.log_map, data.log_webtv_port)
        
        self.listener.parser = parser.parserClass(data, endfunc = self.listener.handle_server_timeout)
        
        self.listener.client_server_address = data.client_address #tuple containing the client's server IP and PORT
        
        self.lip, self.lport = self.listener.server_address #get the listener's address, so it can be sent to the client

        self.client_address = data.client_address
        
        self.end_function = data.end_callback
        self.lthread = None

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
        self.listener.shutdown_listener()
        
    def close_object(self): #only ever called by listener.__listener_shutdown()
        while self.lthread.isAlive(): #attempt to join the socket thread, which will indicate that the listener has properly stopped. this is called from a separate thread to the listener, so it will not block or deadlock
            self.lthread.join(5)
        
        self.logger.info("Listener thread joined. Removing listener object from set")
        
        self.end_function(self) #self is the same as the newListen object added by the daemon
