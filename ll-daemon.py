import SocketServer
import logging
import sys
import os

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

        cip, cport = self.client_address
        cur_pid = os.getpid()

        self.logger.debug('PID %s: Received "%s" from client %s:%s', cur_pid, rcvd, cip, cport)

        #FORMAT OF LOG REQUEST: LIVELOG!KEY!MR_IPGNBOOKER(OPTIONAL)
        tokenized = rcvd.split('!')
        if (tokenized[0] == "LIVELOG"):
            if (tokenized[1] == self.server.LL_API_KEY):
                self.logger.debug('LIVELOG key is correct. Establishing listen socket and returning info')
                #create listen socket

                sip, sport = self.server.server_address

                self.newListen = listener.llListenerObject(sip, self.client_address)

                lport = self.newListen.lport
                self.logger.debug("Listener port: %s", lport)

                returnMsg = "LIVELOG!%s!%s!%s" % (self.server.LL_API_KEY, sip, lport)
                self.logger.debug("RESPONSE: %s", returnMsg)
                self.request.send(returnMsg)

                self.newListen.startListening()

        return

    def finish(self):
        self.logger.debug('Finished handling request from %s:%s', self.cip, self.cport)
        return SocketServer.BaseRequestHandler.finish(self)

class llDaemon(SocketServer.ForkingMixIn, SocketServer.TCPServer):
    def __init__(self, server_ip, handler=llDaemonHandler):
        self.logger = logging.getLogger('llDaemon')
        self.logger.debug('DAEMON INIT')

        self.allow_reuse_address = True

        SocketServer.TCPServer.__init__(self, server_ip, handler)

    def server_activate(self):
        self.logger.debug('Starting TCP listener')

        SocketServer.TCPServer.server_activate(self)

    def serve_forever(self):
        self.logger.debug('Waiting for data')
        while True:
            self.handle()
        return

    def handle(self):
        return SocketServer.TCPServer.handle_request(self)

    def verify_request(self, request, client_ip):
        return SocketServer.TCPServer.verify_request(self, request, client_ip)

    #def process_request(self, request, client_ip):
    #    return SocketServer.TCPServer.process_request(self, request, client_ip)

    def server_close(self):
        return SocketServer.TCPServer.server_close(self)

    #def finish_request(self, request, client_ip):
    #    return SocketServer.TCPServer.finish_request(self, request, client_ip)

    def close_request(self, reqAddress):
        return SocketServer.TCPServer.close_request(self, reqAddress)

if __name__ == '__main__':
    #import threading
    #import socket

    serverAddr = ('192.168.35.128', 61222)

    llServer = llDaemon(serverAddr, llDaemonHandler)
    llServer.LL_API_KEY = "123test"

    #sThread = threading.Thread(target=llServer.serve_forever)
    #sThread.setDaemon(True)
    #sThread.start()
    sip, sport = llServer.server_address

    logger = logging.getLogger('MAIN')
    logger.info("Server on %s:%s under PID %s", sip, sport, os.getpid())

    llServer.serve_forever()