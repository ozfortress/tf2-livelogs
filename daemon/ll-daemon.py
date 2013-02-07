import SocketServer
import socket
import logging
import sys
import os
import threading
import ConfigParser
from pprint import pprint

import listener

log_message_format = logging.Formatter(fmt="%(asctime)s - %(name)s (%(levelname)s): %(message)s", datefmt="%Y-%m-%d %H-%M-%S")

log_file_handler = logging.TimedRotatingFileHandler("daemon.log", when="midnight")
log_file_handler.setFormatter(log_message_format)
log_file_handler.setLevel(logging.WARNING)

log_console_handler = logging.StreamHandler()
log_console_handler.setFormatter(log_message_format)
log_console_handler.setLevel(logging.DEBUG)

class llDaemonHandler(SocketServer.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.logger = logging.getLogger('llDaemonHandler')
        self.logger.addHandler(log_file_handler)
        self.logger.addHandler(log_console_handler)

        self.logger.debug('Handler init. APIKEY: %s', server.LL_API_KEY)

        self.newListen = None
        
        self.cip, self.cport = client_address

        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
        
    def handle(self):
        self.logger.debug('Daemon Handler Handling')
        
        cur_thread = threading.currentThread()
        t_name = cur_thread.name
        
        rcvd = self.request.recv(1024) #read 1024 bytes of data

        self.logger.debug('THREAD %s: Received "%s" from client %s:%s', t_name, rcvd, self.cip, self.cport)

        #FORMAT OF LOG REQUEST: LIVELOG!KEY!SIP!SPORT!MAP!NAME!WEBTV_PORT(OPTIONAL)
        try:
            tokenized = rcvd.split('!')
        except:
            self.logger.debug("Invalid data received")
            return
            
        tokLen = len(tokenized)
        if (tokLen >= 6) and (tokenized[0] == "LIVELOG"):
            if (tokenized[1] == self.server.LL_API_KEY):
                self.logger.debug('LIVELOG key is correct. Establishing listen socket and returning info')
                """ THE IP AND PORT SENT BY THE SERVER PLUGIN. USED TO RECOGNISE THE SERVER
                    client_address cannot be used, because that is the ip:port of the plugin's socket sending the livelogs request
                """
                
                try:
                    socket.inet_pton(socket.AF_INET, tokenized[2]) #if we can do this, it is a valid ipv4 address
                    #socket.inet_pton(socket.AF_INET6, client_ip) srcds does not at this stage support ipv6, and nor do i
                    
                    self.ll_clientip = tokenized[2]
                except:
                    #either invalid address, or dns name sent. let's fix that up
                    dns_res = socket.getaddrinfo(tokenized[2], None, socket.AF_INET) #limit to ipv4
                    
                    if not dns_res:
                        self.logger.debug("Unable to resolve DNS. Rejecting connection")
                        return
                        
                    self.ll_clientip = dns_res[0][4][0] #get the first IP returned by getaddrinfo
                
                self.ll_client_server_port = tokenized[3]

                if (self.server.clientExists(self.ll_clientip, self.ll_client_server_port)):
                    self.logger.debug("THREAD %s: Client %s:%s already has a listener", t_name, self.ll_clientip, self.ll_client_server_port)
                    dict_key = "c" + self.ll_clientip + self.ll_client_server_port
                    listen_ip, listen_port = self.server.clientDict[dict_key]
                    
                    returnMsg = "LIVELOG!%s!%s!%s!REUSE" % (self.server.LL_API_KEY, listen_ip, listen_port)
                    self.logger.debug("RESENDING LISTENER INFO: %s", returnMsg)
                    self.request.send(returnMsg)
                    return    

                sip, sport = self.server.server_address #get our server info, so we know what IP to listen on

                if (tokLen == 6):
                    webtv_port = None

                elif (tokLen == 7):
                    webtv_port = tokenized[6]

                self.newListen = listener.llListenerObject(sip, (self.ll_clientip, self.ll_client_server_port), tokenized[4], tokenized[5], self.server.removeListenerObject,
                                                            timeout=self.server.listener_timeout, webtv_port = webtv_port)
                
                if not self.newListen.listener.parser.HAD_ERROR: #check if the parser had an error during init or not
                    lport = self.newListen.lport #port the listener is on
                    self.logger.debug("THREAD %s: Listener port: %s", t_name, lport)
                    
                    #REPLY FORMAT: LIVELOG!KEY!LISTEN_IP!LISTEN_PORT!UNIQUE_IDENT
                    returnMsg = "LIVELOG!%s!%s!%s!%s" % (self.server.LL_API_KEY, sip, lport, self.newListen.unique_parser_ident)
                    
                    self.logger.debug("RESPONSE: %s", returnMsg)
                    self.request.send(returnMsg)
                    
                    self.server.addClient(self.ll_clientip, self.ll_client_server_port, (sip, lport)) #add the client to a dict and store its listener address

                    self.server.addListenerObject(self.newListen) #add the listener object to a set, so it remains alive
                    
                    self.newListen.startListening() #start listening
                else:
                    self.logger.debug("THREAD %s: Parser had error trying to initialise. Closing connection", t_name)
                    self.newListen.error_cleanup() #shutdown the listener
        else:
            self.logger.debug("THREAD %s: Invalid data received", t_name)

        return
        
    def finish(self):
        if self.newListen:
            self.logger.debug("Finished handling request from %s:%s. Listener established", self.cip, self.cport)
        else:
            self.logger.debug("Finished handling request from %s:%s. Listener not running", self.cip, self.cport)

        self.request.close() #close the connection, as we've finished the request
        
class llDaemon(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_ip, handler=llDaemonHandler):
        self.logger = logging.getLogger('llDaemon')
        self.logger.addHandler(log_console_handler)
        self.logger.debug('DAEMON INIT')
        
        self.allow_reuse_address = True
        self.daemon_threads = True

        self.listen_set = set()
        
        SocketServer.TCPServer.__init__(self, server_ip, handler)
        
    def server_activate(self):
        self.logger.debug('Starting TCP listener and waiting for data')
        
        SocketServer.TCPServer.server_activate(self)

    def addClient(self, ip, port, listen_tuple):
        dict_key = "c" + ip + port
        if dict_key not in self.clientDict:
            self.clientDict[dict_key] = listen_tuple
            self.logger.debug('Added %s:%s to client dict with key %s', ip, port, dict_key)
        
        return

    def clientExists(self, ip, port):
        #print "Keys in self.clientDict: "
        #pprint(self.clientDict.keys())

        dict_key = "c" + ip + port

        if dict_key in self.clientDict:
            self.logger.debug('Key %s is in client dict', dict_key)
            return True
        else:
            self.logger.debug('Key %s is NOT in client dict', dict_key)
            return False

    def removeClient(self, ip, port):
        dict_key = "c" + ip + port
        if dict_key in self.clientDict:
            del self.clientDict[dict_key]
            self.logger.debug('Removed client %s:%s from client dict', ip, port)

        return

    def addListenerObject(self, listener_object):
        #add the listener object to a set
        if listener_object in self.listen_set:
            self.logger.info("Listen object %s is already in the listen set. wat & why?", listener_object)
        else:    
            self.listen_set.add(listener_object)
        
    def removeListenerObject(self, listener_object):
        #removes the object from the set
        if listener_object in self.listen_set:
            self.logger.info("Listener object is in set. Removing")
            client_ip, client_server_port = listener_object.client_address
        
            self.removeClient(client_ip, client_server_port)
            
            self.listen_set.discard(listener_object)
            
            

if __name__ == '__main__':
    cfg_parser = ConfigParser.SafeConfigParser()
    if cfg_parser.read(r'll-config.ini'):
        try:
            server_ip = cfg_parser.get('log-listener', 'server_ip')
                
            serverAddr = (server_ip, cfg_parser.getint('log-listener', 'server_port'))
            api_key = cfg_parser.get('log-listener', 'api_key')
            l_timeout = cfg_parser.getfloat('log-listener', 'listener_timeout')
            
        except:
            print "Unable to read log-listener section in config file"
            quit()
                
    else:
        #first run time, no config file present. create with default values and exit
        print "No configuration file present. A new one will be generated"
        try:
            cfg_file = open(r'll-config.ini', 'w+')
        except:
            print "Unable to open ll-config.ini for writing. Check your permissions"
            quit()
        
        cfg_parser.add_section('log-listener')
        cfg_parser.set('log-listener', 'server_ip', '')
        cfg_parser.set('log-listener', 'server_port', '61222')
        cfg_parser.set('log-listener', 'listener_timeout', '90.0')
        cfg_parser.set('log-listener', 'api_key', '123test')
        cfg_parser.set('log-listener', 'log_directory', 'logs')
        
        cfg_parser.add_section('websocket-server')
        cfg_parser.set('websocket-server', 'server_ip', '')
        cfg_parser.set('websocket-server', 'server_port', '61224')
        cfg_parser.set('websocket-server', 'update_rate', '20.0')
        
        cfg_parser.add_section('database')
        cfg_parser.set('database', 'db_user', 'livelogs')
        cfg_parser.set('database', 'db_password', 'hello')
        cfg_parser.set('database', 'db_name', 'livelogs')
        cfg_parser.set('database', 'db_host', '127.0.0.1')
        cfg_parser.set('database', 'db_port', '5432')
        
        cfg_parser.write(cfg_file)
        
        print "Configuration file generated. Please edit it before running the daemon again"
        quit()
    
    llServer = llDaemon(serverAddr, llDaemonHandler)
    llServer.LL_API_KEY = api_key   
    llServer.clientDict = dict()
    llServer.listener_timeout = l_timeout

    sip, sport = llServer.server_address   

    logger = logging.getLogger('MAIN')
    logger.addHandler(log_console_handler)
    logger.addHandler(log_file_handler)
    
    logger.info("Server on %s:%s under PID %s", sip, sport, os.getpid())
    
    try:
        sthread = threading.Thread(target = llServer.serve_forever())
        sthread.daemon = True
        sthread.start()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt. Closing daemon")
        quit()


def uncaught_excepthook(excType, excValue, traceback, logger=logging.getLogger(__name__)):
    logger.error("Uncaught exception", exc_info=(excType, excValue, traceback))

sys.excepthook = uncaught_excepthook