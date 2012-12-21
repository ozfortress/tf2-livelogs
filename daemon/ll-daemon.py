import SocketServer
import socket
import logging
import sys
import os
import threading
import ConfigParser
from pprint import pprint

import llwebsocket
import listener

logging.basicConfig(level=logging.DEBUG, format='%(name)s: %(message)s')

class llDaemonHandler(SocketServer.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        self.logger = logging.getLogger('llDaemonHandler')
        self.logger.debug('Handler init. APIKEY: %s', server.LL_API_KEY)
        
        self.cip, self.cport = client_address

        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
        
    def setup(self):
        self.logger.debug('Handler setup')
        return SocketServer.BaseRequestHandler.setup(self)
        
    def handle(self):
        self.logger.debug('Daemon Handler Handling')
        
        rcvd = self.request.recv(1024) #read 1024 bytes of data
        
        cur_pid = os.getpid()

        self.logger.debug('PID %s: Received "%s" from client %s:%s', cur_pid, rcvd, self.cip, self.cport)

        #FORMAT OF LOG REQUEST: LIVELOG!KEY!SIP!SPORT!MAP!NAME!WEBTV_PORT(OPTIONAL)
        tokenized = rcvd.split('!')
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
                        
                    self.ll_clientip = dns_res[0][4][0]
                
                self.ll_clientport = tokenized[3]

                if (self.server.clientExists(self.ll_clientip, self.ll_clientport)):
                    self.logger.debug("PID %s: Client %s:%s already has a listener", cur_pid, self.ll_clientip, self.ll_clientport)
                    dict_key = "c" + self.ll_clientip + self.ll_clientport
                    listen_ip, listen_port = self.server.clientDict[dict_key]
                    
                    returnMsg = "LIVELOG!%s!%s!%s!REUSE" % (self.server.LL_API_KEY, listen_ip, listen_port)
                    self.logger.debug("RESENDING LISTENER INFO: %s", returnMsg)
                    self.request.send(returnMsg)
                    return    

                sip, sport = self.server.server_address

                if (tokLen == 6):
                    self.newListen = listener.llListenerObject(sip, (self.ll_clientip, self.ll_clientport), tokenized[4], tokenized[5], timeout=self.server.listener_timeout)

                elif (tokLen == 7):
                    self.newListen = listener.llListenerObject(sip, (self.ll_clientip, self.ll_clientport), tokenized[4], tokenized[5], timeout=self.server.listener_timeout, webtv_port = tokenized[6])

                lport = self.newListen.lport
                self.logger.debug("PID %s: Listener port: %s", cur_pid, lport)
                
                returnMsg = "LIVELOG!%s!%s!%s!%s" % (self.server.LL_API_KEY, sip, lport, self.newListen.unique_parser_ident)
                self.logger.debug("RESPONSE: %s", returnMsg)
                self.request.send(returnMsg)

                self.server.addClient(self.ll_clientip, self.ll_clientport, (sip, lport)) 

                self.newListen.startListening()
                
                self.logger.debug("PID %s: Stopped listening for logs", cur_pid)

                self.server.removeClient(self.ll_clientip, self.ll_clientport)
        else:
            self.logger.debug("PID %s: Invalid data received. Exiting", cur_pid)

        return
        
    def finish(self):
        self.logger.debug('Finished handling request from %s:%s', self.cip, self.cport)

        return SocketServer.BaseRequestHandler.finish(self)
        
class llDaemon(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_ip, handler=llDaemonHandler):
        self.logger = logging.getLogger('llDaemon')
        self.logger.debug('DAEMON INIT')
        
        self.allow_reuse_address = True
        self.daemon_threads = True

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
        print "Keys in self.clientDict: "
        pprint(self.clientDict.keys())

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


if __name__ == '__main__':
    cfg_parser = ConfigParser.SafeConfigParser()
    if cfg_parser.read(r'll-config.ini'):
        try:
            server_ip = cfg_parser.get('log-listener', 'server_ip')
            if server_ip == None:
                #config file has not been edited. need to exit
                print "You need to edit the server_ip in ll-config.ini"
                quit()
                
            serverAddr = (server_ip, cfg_parser.getint(section, 'server_port'))
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
        
        cfg_parser.add_section('websocket-server')
        cfg_parser.set('websocket-server', 'server_ip', '')
        cfg_parser.set('websocket-server', 'server_port', '61224')
        cfg_parser.set('websocket-server', 'update_rate', '20')
        
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
    logger.info("Server on %s:%s under PID %s", sip, sport, os.getpid())
    
    try:
        """
        The websocket is a normal thread, it will start and then continue in the background. The log daemon thread is a daemon thread, and is the keep-alive for the application
        
        """
        
        websocket = llWebSocket()
        webthread = threading.Thread(target = websocket.websocket_start())
        webthread.start()
    
        sthread = threading.Thread(target = llServer.serve_forever())
        sthread.daemon = True
        sthread.start()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt. Shutting down server")
        llServer.shutdown()
        
        logger.info("Exiting")
        quit()
     
        
    #now in threaded serving
