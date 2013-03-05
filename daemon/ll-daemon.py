import logging
import logging.handlers

logging.basicConfig(level=logging.DEBUG, format="[(%(levelname)s) %(process)s %(asctime)s %(module)s:%(name)s:%(lineno)s] %(message)s", datefmt="%H:%M:%S")


try:
    import psycopg2
    import psycopg2.pool
except ImportError:
    print """You are missing psycopg2.
    Install using `pip install psycopg2` or visit http://initd.org/psycopg/
    """
    quit()

import SocketServer
import socket
import sys
import os
import threading
import ConfigParser
from pprint import pprint

import listener

log_message_format = logging.Formatter(fmt="[(%(levelname)s) %(process)s %(asctime)s %(module)s:%(name)s:%(lineno)s] %(message)s", datefmt="%H:%M:%S")

log_file_handler = logging.handlers.TimedRotatingFileHandler("daemon.log", when="midnight")
log_file_handler.setFormatter(log_message_format)
log_file_handler.setLevel(logging.DEBUG)

#this class is used to remove all HTML tags from player strings
class HTMLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = [] #fed is what is fed to the class by the function

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)

def stripHTMLTags(string):
    stripper = HTMLStripper()
    stripper.feed(string)

    return stripper.get_data() #get the text out


class llDaemonHandler(SocketServer.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.logger = logging.getLogger('handler')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(log_file_handler)

        #self.logger.debug('Handler init. APIKEY: %s', server.LL_API_KEY)

        self.newListen = None
        
        self.cip, self.cport = client_address

        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
        
    def handle(self):
        rcvd = self.request.recv(1024) #read 1024 bytes of data

        self.logger.debug('Received "%s" from client %s:%s', rcvd, self.cip, self.cport)

        #FORMAT OF LOG REQUEST: LIVELOG!KEY!SIP!SPORT!MAP!NAME!WEBTV_PORT(OPTIONAL)
        
        try:
            msg = rcvd.split('!')
        except:
            self.logger.debug("Invalid data received")
            return

        msg_len = len(msg)

        if (msg_len >= 6 and msg[0] == "LIVELOG"):
            client_details = self.server.getClientInfo(self.cip)
            self.logger.info("Client details: %s", client_details)

            if client_details is not None and msg[1] == client_details[2]:
                client_api_key = client_details[2]

                self.logger.debug("Key is correct for client %s (%s) @ %s", client_details[0], client_details[1], self.cip)
                        
                try:
                    socket.inet_pton(socket.AF_INET, msg[2]) #if we can do this, it is a valid ipv4 address
                    #socket.inet_pton(socket.AF_INET6, client_ip) srcds does not at this stage support ipv6, and nor do i
                    
                    self.ll_clientip = msg[2]
                except:
                    #either invalid address, or dns name sent. let's fix that up
                    dns_res = socket.getaddrinfo(msg[2], None, socket.AF_INET) #limit to ipv4
                    
                    if not dns_res:
                        self.logger.debug("Unable to resolve DNS. Rejecting connection")
                        return
                        
                    self.ll_clientip = dns_res[0][4][0] #get the first IP returned by getaddrinfo
                
                self.ll_client_server_port = msg[3]

                if self.server.clientExists(self.ll_clientip, self.ll_client_server_port):
                    self.logger.debug("Client %s:%s already has a listener", self.ll_clientip, self.ll_client_server_port)
                    dict_key = "c" + self.ll_clientip + self.ll_client_server_port
                    listen_ip, listen_port = self.server.clientDict[dict_key]
                    
                    returnMsg = "LIVELOG!%s!%s!%s!REUSE" % (client_api_key, listen_ip, listen_port)
                    self.logger.debug("RESENDING LISTENER INFO: %s", returnMsg)
                    self.request.send(returnMsg)
                    return    

                sip, sport = self.server.server_address #get our server info, so we know what IP to listen on

                webtv_port = None

                if (msg_len == 7):
                    try:
                        webtv_port = int(msg[6])
                    except ValueError:
                        self.logger.exception("Invalid webtv port sent. Defaulting to None")
                    except:
                        self.logger.exception("Unknown exception casting webtv_port to int. Defaulting to None")

                log_name = self.escapeString(msg[5])

                self.newListen = listener.llListenerObject(log_file_handler, client_api_key, sip, (self.ll_clientip, self.ll_client_server_port), msg[4], log_name, 
                                                            self.server.removeListenerObject, timeout=self.server.listener_timeout, webtv_port = webtv_port)
                
                if not self.newListen.had_error(): #check if the parser had an error during init or not
                    lport = self.newListen.lport #port the listener is on
                    self.logger.debug("Listener port: %s", lport)
                    
                    #REPLY FORMAT: LIVELOG!KEY!LISTEN_IP!LISTEN_PORT!UNIQUE_IDENT
                    returnMsg = "LIVELOG!%s!%s!%s!%s" % (client_api_key, sip, lport, self.newListen.unique_parser_ident)
                    
                    self.logger.debug("RESPONSE: %s", returnMsg)
                    self.request.send(returnMsg)
                    
                    self.server.addClient(self.ll_clientip, self.ll_client_server_port, (sip, lport)) #add the client to a dict and store its listener address

                    self.server.addListenerObject(self.newListen) #add the listener object to a set, so it remains alive
                    
                    self.newListen.startListening() #start listening
                else:
                    self.logger.debug("Parser had error trying to initialise. Closing connection")
                    self.newListen.error_cleanup() #shutdown the listener

            else:
                #invalid API key, or unable to obtain user details
                self.logger.error("Client %s:%s sent invalid API key, or client is invalid", self.cip, self.cport)
                self.request.send("INVALID_API_KEY")
        else:
            self.logger.debug("Invalid data received")

        return
        
    def escapeString(self, string):
        escaped_string = string.replace("'", "''").replace("\\", "\\\\")
        escaped_string = stripHTMLTags(escaped_string)

        return escaped_string

    def finish(self):
        if self.newListen:
            self.logger.debug("Finished handling request from %s:%s. Listener established", self.cip, self.cport)
        else:
            self.logger.debug("Finished handling request from %s:%s. Listener not running", self.cip, self.cport)

        self.request.close() #close the connection, as we've finished the request


class llDaemon(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_ip, handler=llDaemonHandler):
        self.logger = logging.getLogger('daemon')
        self.logger.debug('DAEMON INIT')
        
        self.allow_reuse_address = True
        self.daemon_threads = True

        self.listen_set = set()

        cfg_parser = ConfigParser.SafeConfigParser()
        if cfg_parser.read(r'll-config.ini'):
            try:
                db_host = cfg_parser.get('database', 'db_host')
                db_port = cfg_parser.getint('database', 'db_port')
                db_user = cfg_parser.get('database', 'db_user')
                db_pass = cfg_parser.get('database', 'db_password')
                db_name = cfg_parser.get('database', 'db_name')

                #using psycopg2 pool wrapper
                db_details = 'dbname=%s user=%s password=%s host=%s port=%s' % (
                            db_name, db_user, db_pass, db_host, db_port)

                self.db = psycopg2.pool.ThreadedConnectionPool(minconn = 1, maxconn = 10, dsn = db_details) #dsn is passed to psycopg2.connect()

            except:
                self.logger.exception("Unable to read database options from config file, or unable to connect to database")
                sys.exit("Unable to read database config or unable to connect to database")

            finally:
                self.logger.info("Successfully connected to database")
        else:
            self.logger.error("Unable to read config file")
            sys.exit("Unable to read config file")
        
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

    def getClientInfo(self, ip):
        #gets the API key for client with IP ip, so IPs will require unique keys, preventing unauthorised users
        if not self.db.closed:
            user_details = None
            try:
                conn = self.db.getconn() #get a connection object from the psycopg2.pool
                
                if conn.closed:
                    self.db.putconn(conn) #garbage the closed connection, and try get a new one
                    conn = self.db.getconn()

                curs = conn.cursor()

                curs.execute("SELECT user_name, user_email, user_key FROM livelogs_auth_keys WHERE user_ip = %s", (ip,))

                user_details = curs.fetchone()

                curs.close()

                self.db.putconn(conn) #put the connection back into the pool. if num conns > minconn, the connection is closed

            except:
                self.logger.exception("Exception trying to get api key for ip %s", ip)
                return None

            finally:
                return user_details

        else:
            self.logger.error("Database pool is closed")
            return None


if __name__ == '__main__':
    cfg_parser = ConfigParser.SafeConfigParser()
    if cfg_parser.read(r'll-config.ini'):
        try:
            server_ip = cfg_parser.get('log-listener', 'server_ip')
                
            serverAddr = (server_ip, cfg_parser.getint('log-listener', 'server_port'))
            l_timeout = cfg_parser.getfloat('log-listener', 'listener_timeout')
            
        except:
            sys.exit("Unable to read log-listener section in config file")
                
    else:
        #first run time, no config file present. create with default values and exit
        print "No configuration file present. A new one will be generated"
        make_new_config()

        sys.exit("Configuration file generated. Please edit it before running the daemon again")
    
    llServer = llDaemon(serverAddr, llDaemonHandler)
    llServer.clientDict = dict()
    llServer.listener_timeout = l_timeout

    sip, sport = llServer.server_address   

    logger = logging.getLogger('MAIN')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(log_file_handler)

    logger.info("Server on %s:%s under PID %s", sip, sport, os.getpid())
    
    try:
        sthread = threading.Thread(target = llServer.serve_forever())
        sthread.daemon = True
        sthread.start()
        
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt. Closing daemon")
        llServer.db.closeall() #close all database connections in the pool

        for listenobj in llServer.listen_set:
            logger.info("Ending log with ident %s", listenobj.unique_parser_ident)
            listenobj.listener.parser.endLogParsing()

        llServer.shutdown()

        logger.info("Shutdown successful")

        sys.exit("KeyboardInterrupt")


def make_new_config():
    try:
        cfg_file = open(r'll-config.ini', 'w+')
    except:
        sys.exit("Unable to open ll-config.ini for writing. Check your permissions")
    
    cfg_parser.add_section('log-listener')
    cfg_parser.set('log-listener', 'server_ip', '')
    cfg_parser.set('log-listener', 'server_port', '61222')
    cfg_parser.set('log-listener', 'listener_timeout', '90.0')
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


def uncaught_excepthook(excType, excValue, traceback, logger=logging.getLogger(__name__)):
    logger.error("Uncaught exception", exc_info=(excType, excValue, traceback))

sys.excepthook = uncaught_excepthook