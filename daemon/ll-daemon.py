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
import time
import threading
import math
import ConfigParser

from HTMLParser import HTMLParser
from pprint import pprint

import listener
from livelib import queryqueue

from livelib.parser_lib import stripHTMLTags

import pdb

log_message_format = logging.Formatter(fmt="[(%(levelname)s) %(process)s %(asctime)s %(module)s:%(name)s:%(lineno)s] %(message)s", datefmt="%H:%M:%S")

log_file_handler = logging.handlers.TimedRotatingFileHandler("daemon.log", when="midnight")
log_file_handler.setFormatter(log_message_format)
log_file_handler.setLevel(logging.DEBUG)

logging.getLogger().addHandler(log_file_handler) #add the file handler to the root logger, so all logs are saved to a file

class llData(object):
    #an object that contains various data which is passed down
    def __init__(self, db, secret, sip, client_address, log_map, log_name, end_callback, timeout, webtv_port):
        self.db = db
        self.client_secret = secret
        self.server_ip = sip
        self.client_address = client_address
        self.log_map = log_map
        self.log_name = log_name
        self.end_callback = end_callback
        self.log_timeout = timeout
        self.log_webtv_port = webtv_port

class llDaemonHandler(SocketServer.BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.logger = logging.getLogger('handler')
        self.logger.setLevel(logging.DEBUG)

        self.newListen = None
        
        self.cip, self.cport = client_address

        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)
        
    def handle(self):
        rcvd = self.request.recv(1024) #read up to 1024 bytes of data

        self.logger.debug('Received "%s" from client %s:%s', rcvd, self.cip, self.cport)

        #FORMAT OF LOG REQUEST: LIVELOG!KEY!SIP!SPORT!MAP!NAME!WEBTV_PORT(OPTIONAL)
        
        try:
            msg = rcvd.split('!')
        except:
            self.logger.debug("Invalid data received")
            return

        msg_len = len(msg)

        if (msg_len > 7):
            #invalid message length
            self.logger.info("Invalid message received. Too many tokens")
            self.request.send("INVALID_MESSAGE")
            return

        if (msg_len >= 6 and msg[0] == "LIVELOG"):
            client_info = self.server.getClientInfo(self.cip)
            self.logger.info("Client info for IP %s: %s", self.cip, client_info)

            client_details = None

            if client_info is not None:
                #client_details is a list of tuples
                for details in client_info:
                    if msg[1] == details[2]: #if the auth key matches one of the returned keys
                        client_details = details #copy the details to our individual client's details

            if client_details is not None:
                client_api_key = client_details[2]

                self.logger.info("Key is correct for client %s (%s) @ %s", client_details[0], client_details[1], self.cip)

                if self.resolve_dns(msg[2]):
                    #msg[2] is an IP, so use the api key as the log secret
                    client_secret = client_api_key
                
                else:
                    #msg[2] is not an IP, so use it as the log secret
                    client_secret = msg[2]
                
                self.ll_clientip = self.cip #use the IP used for this connection as the server's address
                self.ll_clientport = msg[3]

                old_listener = self.server.get_client_listener(self.ll_clientip, self.ll_clientport)
                if old_listener:
                    self.logger.info("Client %s:%s already has a listener", self.ll_clientip, self.ll_clientport)
                    
                    if msg[4] != old_listener.data.log_map and not old_listener.listener.parser.LOG_PARSING_ENDED:
                        #client changed maps, so this log needs to be ended and a new one started
                        self.logger.info("Request has different map. Ending old listener")
                        old_listener.listener.shutdown_listener() #end the log and close the listener

                    else:
                        returnMsg = "LIVELOG!%s!%s!%s!REUSE" % (client_api_key, old_listener.listen_ip, old_listener.listen_port)
                        self.logger.debug("RESENDING LISTENER INFO: %s", returnMsg)
                        self.request.send(returnMsg)
                        return

                sip = self.server.server_address[0] #get our server info, so we know what IP to listen on
                webtv_port = None

                if (msg_len == 7):
                    try:
                        webtv_port = int(msg[6])
                    except ValueError:
                        self.logger.exception("Invalid webtv port sent. Defaulting to None")
                    except:
                        self.logger.exception("Unknown exception casting webtv_port to int. Defaulting to None")

                log_name = self.escapeString(msg[5])

                data_obj = llData(self.server.db, client_secret, sip, (self.ll_clientip, self.ll_clientport), msg[4], log_name,
                                    self.server.removeListenerObject, self.server.listener_timeout, webtv_port)

                data_obj.weapon_data = self.server.weapon_data
                data_obj.query_queue = self.server.query_queue

                self.newListen = listener.llListenerObject(data_obj)
                
                if not self.newListen.had_error(): #check if the parser had an error during init or not
                    lport = self.newListen.listen_port #port the listener is on
                    #self.logger.debug("Listener port: %s", lport)
                    
                    #REPLY FORMAT: LIVELOG!KEY!LISTEN_IP!LISTEN_PORT!UNIQUE_IDENT
                    returnMsg = "LIVELOG!%s!%s!%s!%s" % (client_api_key, sip, lport, self.newListen.get_numeric_id())
                    
                    self.logger.debug("RESPONSE: %s", returnMsg)
                    self.request.send(returnMsg)
                    
                    self.server.add_client(self.ll_clientip, self.ll_clientport, self.newListen) #add the client to a dict and store its listener

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

    def resolve_dns(self, ip):
        try:
            socket.inet_pton(socket.AF_INET, ip) #if we can do this, it is a valid ipv4 address
            #socket.inet_pton(socket.AF_INET6, client_ip) srcds does not at this stage support ipv6, and nor do i
            
            return ip
        except:
            #either invalid address, or dns name sent. let's fix that up
            try:
                dns_res = socket.getaddrinfo(ip, None, socket.AF_INET) #limit to ipv4
            except:
                #error using getaddrinfo (parameter supplied is not an IP address)
                return None
            
            if not dns_res:
                return None
                
            return dns_res[0][4][0] #get the first IP returned by getaddrinfo

    def finish(self):
        if self.newListen:
            self.logger.debug("Finished handling request from %s:%s. Listener established", self.cip, self.cport)
        else:
            self.logger.debug("Finished handling request from %s:%s. Listener already running, or not established", self.cip, self.cport)

        self.server.close_request(self.request) #close the connection, as we've finished the request



class llDaemon(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_address, l_timeout, process_frequency, min_process_quota, max_process_quota, client_handler=llDaemonHandler):
        self.logger = logging.getLogger('daemon')

        self.allow_reuse_address = True
        self.daemon_threads = True

        self.clientDict = {}
        self.listen_set = set()

        self.listener_timeout = l_timeout

        self.weapon_data = {} #empty until it's updated by the thread

        self.timeout_event = threading.Event()
        self.timeout_thread = threading.Thread(target=self._listener_timeout_timer, args=(self.timeout_event,))
        self.timeout_thread.daemon = True

        self.query_queue = queryqueue.query_queue() #our query queue object
        self.queue_process_frequency = process_frequency
        self.queue_min_quota = min_process_quota
        self.queue_max_quota = max_process_quota

        self.queue_process_event = threading.Event()
        self.queue_process_thread = threading.Thread(target=self._process_queue_timer, args=(self.queue_process_event,))
        self.queue_process_thread.daemon = True

        self.__daemon_lock = threading.Lock()


        self._weapon_thread = threading.Thread(target=self.__get_weapon_data)
        self._weapon_thread.daemon = True

        SocketServer.TCPServer.__init__(self, server_address, client_handler)
        
    def server_activate(self):
        self.logger.debug('Starting TCP listener')
        
        SocketServer.TCPServer.server_activate(self)

    def add_client(self, ip, port, listener):
        dict_key = "c" + ip + port
        if dict_key not in self.clientDict:
            self.clientDict[dict_key] = listener
            #self.logger.debug('Added %s:%s to client dict with key %s', ip, port, dict_key)
        
        return

    def get_client_listener(self, ip, port):
        #print "Keys in self.clientDict: "
        #pprint(self.clientDict.keys())

        dict_key = "c" + ip + port
        self.__daemon_lock.acquire() #use a lock to prevent another thread from deleting while checking

        result = None
        if dict_key in self.clientDict:
            #self.logger.debug('Key %s is in client dict', dict_key)
            result = self.clientDict[dict_key]

        self.__daemon_lock.release()

        return result

    def remove_client(self, ip, port):
        dict_key = "c" + ip + port
        if dict_key in self.clientDict:
            del self.clientDict[dict_key]
            #self.logger.debug('Removed client %s:%s from client dict', ip, port)

        return

    def addListenerObject(self, listener_object):
        #add the listener object to a set
        if listener_object in self.listen_set:
            self.logger.info("Listen object %s is already in the listen set. wat & why?", listener_object)
        else:
            self.__daemon_lock.acquire() #use lock so that another thread doesnt add/remove to/from the set at the same time
            self.listen_set.add(listener_object)
            self.__daemon_lock.release()
        
    def removeListenerObject(self, listener_object):
        #removes the object from the set
        if listener_object in self.listen_set:
            self.__daemon_lock.acquire() #lock so another thread doesn't add/remove at the same time
            #self.logger.info("Listener object is in set. Removing")
            client_ip, client_server_port = listener_object.client_address
        
            self.remove_client(client_ip, client_server_port)
            
            self.listen_set.discard(listener_object)

            self.__daemon_lock.release()
        else:
            self.logger.info("There was an attempt to remove a listener object that is not in the listener set")

    def getClientInfo(self, ip):
        """
        gets the API key for client with IP ip, so IPs will require unique keys, preventing unauthorised users
        users using hosted implementations may have the same IP, however, so we need to check all results for an
        auth key match
        """

        if not self.db.closed:
            user_details = None
            curs = None
            conn = None
            try:
                try:
                    conn = self.db.getconn() #get a connection object from the psycopg2.pool
                except:
                    self.logger.exception("Exception getting database connection")

                    return user_details
                
                conn_retries = 0
                while conn.closed: #this loop will only run if the connection is closed, and will atempt to reconnect 5 times (over a span of 10 seconds)
                    self.logger.info("Database connection is closed. Getting a new one. Attempt: %d", conn_retries)
                    if conn_retries == 5:
                        self.logger.error("Unable to reconnect to database")
                        self.db.putconn(conn)

                        return None

                    self.db.putconn(conn) #garbage the closed connection, and try get a new one
                    conn = self.db.getconn()

                    conn_retries += 1

                    time.sleep(2)

                curs = conn.cursor()

                curs.execute("SELECT user_name, user_email, user_key FROM livelogs_auth_keys WHERE user_ip = %s", (ip,))

                user_details = curs.fetchall()

            except:
                self.logger.exception("Exception trying to get api key for ip %s", ip)
                conn.rollback()

            finally:
                if curs and not curs.closed:
                    curs.close()
                if conn:
                    self.db.putconn(conn)

                return user_details

        else:
            self.logger.error("Database pool is closed")
            return None

    def prepare_server(self):
        self.__open_dbpool()

        self.queue_process_thread.start()
        self.timeout_thread.start()

        self._weapon_thread.start()

    def __open_dbpool(self):
        #open database pool
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

                self.db = psycopg2.pool.ThreadedConnectionPool(minconn = 2, maxconn = 5, dsn = db_details) #dsn is passed to psycopg2.connect()

            except:
                self.logger.exception("Unable to read database options from config file, or unable to connect to database")
                sys.exit("Unable to read database config or unable to connect to database")

            finally:
                self.logger.info("Successfully connected to database")
        else:
            self.logger.error("Unable to read config file")
            sys.exit("Unable to read config file")

    def listenerTimeoutCheck(self):
        #loop over the listener objects to see if any of them have timed out
        listeners = self.listen_set.copy() #shallow copy the set, so we can iterate over it without worrying about issues when new objects are added

        current_ctime = time.time() #store the current time, so we don't need to get it for every object being iterated

        try:
            for listen_object in listeners:

                #first check if the log has ended
                if listen_object.listener._ended:
                    #the game has ended. call the shutdown method
                    listen_object.listener.shutdown_listener()

                elif listen_object.listener.timed_out(current_ctime):
                    #the listener has timed out
                    listen_object.listener.handle_server_timeout()

        except KeyboardInterrupt:
            return
        except:
            self.logger.exception("Exception looping over listeners for timeout")


    def _listener_timeout_timer(self, event):
        while not event.is_set():
            self.listenerTimeoutCheck()

            event.wait(2) #run a timeout check every 2 seconds

    def __process_database_queue(self, process_quota):
        """
        this will process a queue of database queries that are required to be performed by parser objects
        each stat upsert or similar query is added to this queue. things like event queries, or chat queries that
        require something to be returned are not done using this queue, as they have a higher priority
        """
        if self.db.closed:
            self.logger.error("DB POOL IS CLOSED, CANNOT PROCESS DATABASE QUEUE. PLZ RESTART")
            return

        try:
            conn = self.db.getconn() #get a connection object from the psycopg2.pool
        except:
            self.logger.exception("Exception getting database connection")
            return

        cursor = conn.cursor()

        try:
            commit_threshold = int(math.ceil(process_quota / 4))
            queries_completed = 0
            for i in xrange(0, process_quota): #process at most 'process_quota' queries every queue cycle
                cursor.execute("SAVEPOINT queue_savepoint")

                query_tuple = self.query_queue.get_next_query()

                if query_tuple: #if we have queries to execute
                    query_a = query_tuple[0]
                    query_b = query_tuple[1]

                    #print "process iter %d: query: %s" % (i, query_tuple)

                    if query_a and query_b:
                        #we have an insert/update query (upsert). query_a is the insert, query_b is the update
                        try:
                            cursor.execute("SELECT pgsql_upsert(%s, %s)", (query_a, query_b,))
                            
                        except:
                            self.logger.exception("ERROR UPSERTING. INSERT QUERY: \"%s\" | UPDATE QUERY: \"%s\"" % (query_a, query_b))
                            cursor.execute("ROLLBACK TO SAVEPOINT queue_savepoint") #rollback to savepoint
                            #self.query_queue.readd_query(query_tuple) #re-add the query

                    else:
                        #we just have a single query to perform
                        try:
                            cursor.execute(query_a)
                        except:
                            self.logger.exception("ERROR INSERTING. INSERT QUERY: \"%s\"" % (query_a))
                            cursor.execute("ROLLBACK TO SAVEPOINT queue_savepoint") #rollback to savepoint
                            #self.query_queue.readd_query(query_tuple) #re-add the query
                else:
                    #nothing in any queues, just break out until next loop
                    break

                queries_completed += 1
                if queries_completed == commit_threshold:
                    conn.commit() #commit changes to database every commit_threshold 
                    queries_completed = 0

            if queries_completed > 0:
                conn.commit() #commit any changes that havent been committed yet

        except:
            self.logger.exception("ERROR PROCESSING QUERY QUEUE")

        if not conn.closed:
                cursor.close()

        self.db.putconn(conn)

    def _process_queue_timer(self, event):
        while not event.is_set():
            if not self.query_queue.queues_empty():
                norm_queue_length = self.query_queue.queue_length(queryqueue.NMPRIO)
                dynamic_quota = norm_queue_length / 4 #process 1/4 of the queue each run, for a minimum of 200

                #cap the process quota at the configured min/maximum
                if dynamic_quota > self.queue_max_quota:
                    dynamic_quota = self.queue_max_quota
                elif dynamic_quota < self.queue_min_quota:
                    dynamic_quota = self.queue_min_quota

                self.logger.debug("queue lengths: %s, dynamic quota: %s", self.query_queue.queue_length_all(), dynamic_quota)

                self.__process_database_queue(dynamic_quota)

                #pdb.set_trace()

            event.wait(self.queue_process_frequency) #run a time

    def __get_weapon_data(self):
        from livelib import sapi_data

        sapi = sapi_data.Steam_API()
        self.weapon_data = sapi.get_default_weapons() #make the weapon data the default shit until the API is g2g
        self.logger.info("Weapon data is now default")
        #this usually takes some time, so we just let this bitch do its shit in the thread

        sapi.get_item_data_loc() #required for more than non-static weapon log names
        self.weapon_data = sapi.get_item_data()

        self.logger.info("Weapon data now contains custom weapons")

if __name__ == '__main__':
    cfg_parser = ConfigParser.SafeConfigParser()
    if cfg_parser.read(r'll-config.ini'):
        try:
            server_ip = cfg_parser.get('log-listener', 'server_ip')
            server_port = cfg_parser.getint('log-listener', 'server_port')

            l_timeout = cfg_parser.getfloat('log-listener', 'listener_timeout')

            process_frequency = cfg_parser.getfloat('log-listener', 'queue_process_frequency') #how often (in seconds) the query queue should be processed
            min_quota = cfg_parser.getint('log-listener', 'queue_min_quota') #min num of queries to process
            max_quota = cfg_parser.getint('log-listener', 'queue_max_quota') #how many queries should be processed per interval (MAX)
            
        except:
            sys.exit("Error reading config file")
                
    else:
        #first run time, no config file present. create with default values and exit
        print "No configuration file present. A new one will be generated in ll-config.ini"
        make_new_config()

        sys.exit("Configuration file generated. Please edit it before running the daemon again")

    server_address = (server_ip, server_port)

    llServer = llDaemon(server_address, l_timeout, process_frequency, min_quota, max_quota, client_handler=llDaemonHandler)

    logger = logging.getLogger('MAIN')
    logger.setLevel(logging.DEBUG)

    llServer.prepare_server() #start threads/get database connection pool

    logger.info("Server on %s:%s under PID %s", server_address[0], server_address[1], os.getpid())

    try:
        logger.info("Waiting for incoming data")
        llServer.serve_forever() #listen for log requests!
        
    except KeyboardInterrupt:
        #clean up the listener objects/parsers still running

        logger.info("Keyboard interrupt. Closing daemon")
        llServer.timeout_event.set() #stop the timeout thread
        llServer.timeout_thread.join(2) #wait 2 secs for thread to join before closing the interpreter

        #shallow copy of the listen object set, so it can be iterated on while items are being removed
        for listenobj in llServer.listen_set.copy():
            logger.info("Ending log with ident %s", listenobj.unique_parser_ident)

            if not listenobj.listener.parser.LOG_PARSING_ENDED:
                listenobj.listener.parser.endLogParsing(shutdown=True)
                listenobj.listener.shutdown_listener()
                
            else:
                logger.info("\tListen object is still present, but the log has actually ended")

        #stop the queue processing once we're relatively certain the queue has been processed entirely
        llServer.queue_process_event.set() #stop the queue processing event
        llServer.queue_process_thread.join(5) #5 second join timeout

        llServer.db.closeall() #close all database connections in the pool

        llServer.shutdown() #stop listening
        llServer.server_close() #close socket

        logger.info("Shutdown successful")

        sys.exit("KeyboardInterrupt")

    except:
        logger.exception("Exception listening for log requests")

        if not llServer.db.closed:
            llServer.db.closeall()

        sys.exit(2)


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
    cfg_parser.set('log-listener', 'queue_process_frequency', '0.5')
    cfg_parser.set('log-listener', 'queue_min_quota', '200')
    cfg_parser.set('log-listener', 'queue_max_quota', '2000')
    
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
