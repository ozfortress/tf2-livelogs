import SocketServer
import socket
import logging
import sys
import os
import threading
from pprint import pprint


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
                #---- THE IP AND PORT SENT BY THE SERVER PLUGIN. USED TO RECOGNISE THE SERVER
                #---- client_address cannot be used, because that is the ip:port of the plugin's socket sending the livelogs request
                
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
                    self.logger.debug("PID %s: Client %s:%s already has a listener ?", cur_pid, self.ll_clientip, self.ll_clientport)
                    dict_key = "c" + self.ll_clientip + self.ll_clientport
                    listen_ip, listen_port = self.server.clientDict[dict_key]
                    
                    returnMsg = "LIVELOG!%s!%s!%s!REUSE" % (self.server.LL_API_KEY, listen_ip, listen_port)
                    self.logger.debug("RESENDING LISTENER INFO: %s", returnMsg)
                    self.request.send(returnMsg)
                    return    

                sip, sport = self.server.server_address

                if (tokLen == 6):
                    self.newListen = listener.llListenerObject(sip, (self.ll_clientip, self.ll_clientport), tokenized[4], tokenized[5])

                elif (tokLen == 7):
                    self.newListen = listener.llListenerObject(sip, (self.ll_clientip, self.ll_clientport), tokenized[4], tokenized[5], webtv_port = tokenized[6])

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

        #self.newListen.listener.server_close()
        #self.server.removeClient(self.ll_clientip, self.ll_clientport)

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
        #self.addClient(ip, port)

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
    serverAddr = ('192.168.35.128', 61222)
    
    llServer = llDaemon(serverAddr, llDaemonHandler)
    llServer.LL_API_KEY = "123test"    
    llServer.clientDict = dict()

    sip, sport = llServer.server_address   

    logger = logging.getLogger('MAIN')
    logger.info("Server on %s:%s under PID %s", sip, sport, os.getpid())
    
    sthread = threading.Thread(target = llServer.serve_forever())
    sthread.daemon = True
    sthread.start()
    #llServer.serve_forever()

    #wat do?
