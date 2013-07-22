"""
Websocket stuff, for dynamic updating of stats and sourcetv 2d relay

"""
try:
    import tornado
    import tornado.options
    import tornado.websocket
    import tornado.web
    import tornado.ioloop
    import tornado.escape
    from tornado import gen
except ImportError:
    print """You are missing tornado. 
    Install tornado using `pip install tornado`, or visit http://www.tornadoweb.org/
    """
    quit()
    
import logging
import logging.handlers
import time
import threading
import sys
import ConfigParser

from livelib import dbmanager
from livelib import ws_clientdata

from pprint import pprint

try:
    import momoko
except ImportError:
    print """Momoko is missing from the daemon directory, or is not installed in the python library
    Visit https://github.com/FSX/momoko to obtain the latest revision
    """
    
    quit()

log_message_format = logging.Formatter(fmt="[(%(levelname)s) %(process)s %(asctime)s %(module)s:%(name)s:%(lineno)s] %(message)s", datefmt="%H:%M:%S")

log_file_handler = logging.handlers.TimedRotatingFileHandler("websocket-server.log", when="midnight")
log_file_handler.setFormatter(log_message_format)
log_file_handler.setLevel(logging.DEBUG)

class llWSApplication(tornado.web.Application):
    def __init__(self, update_rate=10):
        handlers = [
            (r"/logupdate", logUpdateHandler),
            (r"/webrelay", webtvRelayHandler),
        ]
        
        settings = {
            "cookie_secret": "12345"
        }

        self.logger = logging.getLogger("WS APP")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(log_file_handler)

        self.update_rate = update_rate
        
        self.__db_managers = {} #dict containing db managers wrt to log idents

        self.log_cache = [] #holds a set of tuples containing log idents, the last time they were updated, and the status (live/not live) | [(cache_time, log_ident, status<t/f>), (cache_time, log_ident, status<t/f>)]

        self.clients = ws_clientdata.client_data() #a client_data object, which contains all valid/invalid clients

        self.log_update_thread_event = threading.Event()
        self.log_update_thread = threading.Thread(target = self._send_update_timer, args=(self.log_update_thread_event,))
        self.log_update_thread.daemon = True
        self.log_update_thread.start()

        self.status_update_thread_event = threading.Event()
        self.status_update_thread = threading.Thread(target = self._status_timer, args=(self.status_update_thread_event,))
        self.status_update_thread.daemon = True
        self.status_update_thread.start()

        self.__manager_threading_lock = threading.Lock()
        self.__cache_threading_lock = threading.Lock()
        self.__end_lock = threading.Lock() #a lock to prevent logs being ended whilst they are being status checked
        self.database_lock = threading.Lock() #a lock that is passed down to the db managers. this will prevent multiple db managers from trying to get status at the same time

        tornado.web.Application.__init__(self, handlers, **settings)
            
    def add_to_cache(self, log_ident, status):
        self.__cache_threading_lock.acquire()

        self.log_cache.append((int(round(time.time())), log_ident, status))

        self.__cache_threading_lock.release()
        
    def remove_from_cache(self, cache_item, locked=False):
        if not locked:
            self.__cache_threading_lock.acquire()

        self.log_cache.remove(cache_item)

        if not locked:
            self.__cache_threading_lock.release()
        
        self.logger.debug("Removed cache item %s", cache_item)

    def update_cache(self, log_ident, status):
        #updates the status of a log ident

        self.__cache_threading_lock.acquire()

        for log_cache in self.log_cache.copy():
            if log_ident == log_cache[1]:
                self.remove_from_cache(log_cache, locked = True)
                break

        self.__cache_threading_lock.release()

        self.add_to_cache(log_ident, status)
    
    def get_log_cache(self, log_ident):
        #return a cache only if the cache is valid
        self.__cache_threading_lock.acquire()

        rtn = None

        for log_cache in self.log_cache:
            if log_cache[1] == log_ident: #log_cache = (cache_time, log_ident, status<t/f>)
                time_ctime = int(round(time.time()))

                time_diff = time_ctime - log_cache[0]

                if log_cache[2] == False:
                    expiry_threshold = 600 #10 minute expiry on non-live caches
                else:
                    expiry_threshold = 60 #60 second expiry on live caches

                if time_diff > expiry_threshold:
                    #cache expired
                    self.remove_from_cache(log_cache, locked = True)
                    break

                else:
                    rtn = log_cache

        self.__cache_threading_lock.release()

        return rtn

    def add_client(self, client_obj):
        log_ident = client_obj._log_ident

        if not log_ident:
            self.logger.debug("Client attempted adding without a log ident??")
            client.close()

            return

        log_cache = self.get_log_cache(log_ident)

        if not log_cache:
            #we're unsure if this log is valid
            add_res = self.clients.add_client(client_obj)
            
            if add_res == True:
                #log was not cached, but the client was added to a valid log ident. therefore, the log is still valid and should be re-added to the cache as such
                self.add_dbmanager(log_ident)

                self.add_to_cache(log_ident, True)
                client.write_message("LOG_IS_LIVE")

            #else, the client was added to the invalid list which will be checked by the status thread


        else:
            #we know the log is valid, so we can check the live status
            if log_cache[2] == True:
                self.add_dbmanager(log_ident)

                self.__add_valid_client(client_obj, cache_valid = True)
                client.write_message("LOG_IS_LIVE")

            else:
                #log is not live, disconnect the client
                client_obj.disconnect_not_live()

    def delete_client(self, client_obj):
        self.logger.info("Deleting client")
        if client_obj._log_ident:
            self.clients.delete_client(client_obj)

    def add_live_ident(self, log_ident, tstamp):
        #log_ident is live after status check, so establish a db manager if it doesn't exist, and move clients to valid queue

        self.logger.debug("Moving log ident %s from invalid to valid. Time: %s", log_ident, tstamp)

        self.clients.move_invalid_ident(log_ident)
        self.add_dbmanager(log_ident, tstamp)
        

    def close_invalid(self, log_ident, not_live = False):
        #closes clients associated with the 'invalid' log ident, either because the log is not live or the log is actually invalid

        self.logger.debug("Deleting invalid ident %s. not_live: %d", log_ident, not_live)
            
        clients = self.clients.get_ivclients(log_ident)
        if clients:
            for client in clients:
                if not_live: #we're deleting this log because it's not live
                    client.disconnect_not_live()
                else: #we're deleting this log because it's invalid, and no status could be obtained
                    client.close()

        self.clients.delete_ident(log_ident)

    def add_dbmanager(self, log_ident, tstamp):
        self.__manager_threading_lock.acquire()

        if log_ident not in self.__db_managers:
            self.__db_managers[log_ident] = self.__get_dbmanager(log_ident, tstamp)

        self.__manager_threading_lock.release()

    def __get_dbmanager(self, log_ident, tstamp):
        #creates a new db manager object and returns it
        return dbmanager.dbManager(self.db, log_ident, self.database_lock, self.update_rate, tstamp)

    def __end_log(self, log_ident):
        #deletes a db manager and associated clients
        self.__manager_threading_lock.acquire()
        end_update_dict = None

        if log_ident in self.__db_managers:
            end_update_dict = self.__db_managers[log_ident].full_update()

            self.__db_managers[log_ident].cleanup()

            del self.__db_managers[log_ident]

        self.__manager_threading_lock.release()

        clients = self.clients.get_vclients(log_ident)
        if clients:
            for client in clients:
                client.disconnect_end(end_update_dict)

        self.clients.delete_ident(log_ident)

        self.update_cache(log_ident, False)

    def _send_update_timer(self, event):
        #this method is run in a thread, and acts as a timer
        while not event.is_set():
            self.__send_log_updates()

            event.wait(self.update_rate)

    def __send_log_updates(self):
        valid_idents = self.clients.get_valid_idents()
        num_idents = len(valid_idents)

        self.logger.debug("Sending updates. Number of active logs: %d", num_idents)

        if num_idents == 0:
            return

        try:
            self.__manager_threading_lock.acquire()

            for log_id in valid_idents:
                if self.clients.get_num_vclients(log_id) == 0:
                    continue

                if log_id in self.__db_managers:
                    log_manager = self.__db_managers[log_id]

                else:
                    #no log manager exists for this... how & why?
                    self.logger.error("log %s has clients and is considered valid, but has no db manager?")
                    continue

                delta_update_dict = log_manager.compressed_update()
                full_update_dict = log_manager.full_update()

                for client in self.clients.get_vclients(log_id):
                    #client is a websocket client object, which data can be sent to using client.write_message, etc
                    client.write_message("HELLO!")
                    if not client.HAD_FIRST_UPDATE:
                        #need to send complete values on first update to keep clients in sync with the server
                        if full_update_dict:
                            #send a complete update to the client
                            client.write_message(full_update_dict)
                        
                            client.HAD_FIRST_UPDATE = True
                    else:
                        self.logger.debug("Got update dict for %s: %s", log_id, delta_update_dict)
                        if delta_update_dict: #if the dict is not empty, send it. else, just keep processing and waiting for new update
                            self.logger.debug("Sending update to client %s", client.cip)
                            client.write_message(delta_update_dict)
        except:
            self.logger.exception()

        finally:
            self.__manager_threading_lock.release()

    def _log_finished_callback(self, log_ident):
        self.logger.info("Log id %s is over. Closing connections", log_ident)
        self.__end_lock.acquire()

        self.__end_log(log_ident)

        self.__end_lock.release()

    def _status_timer(self, event):
        while not event.is_set():
            self.__process_log_status()

            event.wait(self.update_rate)

    def __process_log_status(self):
        self.logger.debug("Getting log status")
        try:
            self.__end_lock.acquire()

            self._invalid_idents = self.clients.get_invalid_idents() #a list of log idents in the invalid dict
            self._valid_idents = self.clients.get_valid_idents()
            
            log_idents = self._invalid_idents + self._valid_idents
            self.logger.debug("Current log idents: %s", log_idents)

            if len(log_idents) == 0:
                self.logger.debug("No log idents present to check status for")

                self.__end_lock.release()
                return

            #create a select statement to get status of all log idents in the queue
            filter_string = ""

            for log_ident in log_idents:
                if len(filter_string) > 0:
                    filter_string += " OR "

                filter_string += "log_ident = E'%s'" % (log_ident)

            select_query = "SELECT log_ident, live, tstamp FROM livelogs_log_index WHERE (%s)" % (filter_string)

            self.logger.info("status query: %s", select_query)

            try:
                self.db.execute(select_query, callback = self._status_callback)
            except:
                self.logger.exception()
                
        except:
            self.logger.exception()
        finally:
            self.__end_lock.release()
    
    @tornado.web.asynchronous
    def _status_callback(self, cursor, error):
        if error:
            self.application.logger.error("Error querying database for log status")

            return

        #if live is NOT NULL, then the log exists
        #live == t means the log is live, and live == f means it's not live
        self.logger.debug("queue log status callback")

        results = cursor.fetchall() #fetchall returns a list of tuples of all results
        
        if results and len(results) > 0:
            for log_status in results: #log_status is a tuple in form (log_ident, live)
                self.logger.debug("log_status tuple: %s", log_status)
                log_ident, live, tstamp = log_status

                self.add_to_cache(log_ident, live)

                if live == True:
                    self.logger.debug("log is live")

                    if log_ident in self._invalid_idents:
                        #move the queue to the dict of valid log idents
                        self.add_live_ident(log_ident, tstamp)
                    
                else:
                    self.application.logger.debug("log is not live, disconnecting clients")
                    if log_ident in self._valid_idents:
                        #valid ident is no longer live, close it
                        self._log_finished_callback(log_ident) #run the ending callback

                    else:
                        #unknown ident is not live
                        self.close_invalid(log_ident, not_live = True)

                self._invalid_idents.remove(log_ident)


        #if idents are still in the invalid dict... delete them because they are actually invalid and do not exist
        for log_ident in self._invalid_idents:
            self.close_invalid(log_ident)


class webtvRelayHandler(tornado.websocket.WebSocketHandler):
    pass
        
class logUpdateHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        self._log_ident_received = False
        self._log_ident = None

        self.__valid_log_received = False
        
        self.HAD_FIRST_UPDATE = False
        
        tornado.websocket.WebSocketHandler.__init__(self, application, request, **kwargs)
    
    def open(self):
        #client connects
        #inherits object "request" (which is a HTTPRequest object defined in tornado.httpserver) from tornado.web.RequestHandler

        self.application.logger.info("Client connected. IP: %s", self.request.remote_ip)

        self.cip = self.request.remote_ip
        
    def on_close(self):
        #client disconnects
        self.application.logger.info("Client disconnected. IP: %s", self.request.remote_ip)

        self.application.delete_client(self)

        return
        
    def on_message(self, msg):
        #client will send the log ident upon successful connection
        self.application.logger.info("Client %s sent msg: %s", self.request.remote_ip, msg)

        if (self._log_ident_received):
            self.application.logger.debug("Client %s has already sent log ident \"%s\"", self.request.remote_ip, self._log_ident)
            return
        
        #a standard message will be a json encoded message with key "ident"
        #i.e [ "ident" : 2315363_121212_1234567]
        try:
            parsed_msg = tornado.escape.json_decode(msg) 
            
        except ValueError:
            self.application.logger.exception("ValueError trying to decode message")
            
            self.close()
            
            return
            
        log_ident = str(parsed_msg["ident"])
        if not log_ident:
            #invalid message received, disconnect this bitch

            self.close()

            return
        
        self._log_ident_received = True
        self._log_ident = log_ident
        
        self.application.logger.debug("Received log ident '%s'", log_ident)

        self.application.add_client(self)
                
    def disconnect_not_live(self):
        if self:
            self.write_message("LOG_NOT_LIVE")
        
            self.close()

    def disconnect_end(self, end_update = None):
        if self:
            if end_update:
                self.write_message(end_update)

            self.write_message("LOG_END")

            self.close()
            
if __name__ == "__main__": 
    cfg_parser = ConfigParser.SafeConfigParser()
    if cfg_parser.read(r'll-config.ini'):
        try:
            db_host = cfg_parser.get('database', 'db_host')
            db_port = cfg_parser.getint('database', 'db_port')
            db_user = cfg_parser.get('database', 'db_user')
            db_pass = cfg_parser.get('database', 'db_password')
            db_name = cfg_parser.get('database', 'db_name')
            
            server_ip = cfg_parser.get('websocket-server', 'server_ip')
            server_port = cfg_parser.getint('websocket-server', 'server_port')
            update_rate = cfg_parser.getfloat('websocket-server', 'update_rate')
            
        except:
            print "Unable to read websocket and or database section in config file. Please ensure you've run the daemon once, which generates the config file"
            quit()
    else:
        print "Error reading config file"
        quit()
    
    logger = logging.getLogger('WS MAIN')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(log_file_handler)

    logger.info("Successfully read config")
    
    db_details = 'dbname=%s user=%s password=%s host=%s port=%s' % (
                db_name, db_user, db_pass, db_host, db_port)
    
    #support command line options, which will override whatever is set in the config
    tornado.options.define("ip", default=server_ip, help="Address the websocket server will listen on", type=str)
    tornado.options.define("port", default=server_port, help="Port the websocket server will listen on", type=int)
    tornado.options.define("update_rate", default=update_rate, help="The rate at which updates are pushed (seconds)", type=float)
    
    tornado.options.parse_command_line()
    
    llWebSocketServer = llWSApplication(update_rate = tornado.options.options.update_rate)
        
    llWebSocketServer.db = momoko.Pool(
            dsn = db_details,
            minconn = 2, #minimum number of connections for the momoko pool to maintain
            maxconn = 4, #max number of conns that will be opened
            cleanup_timeout = 10, #how often (in seconds) connections are closed (cleaned up) when number of connections > minconn
        )
    
    llWebSocketServer.listen(tornado.options.options.port, tornado.options.options.ip)
    logger.info("Websocket server listening on %s:%s", tornado.options.options.ip, tornado.options.options.port)
    
    try:
        tornado.ioloop.IOLoop.instance().start()
    except:
        llWebSocketServer.db.close()
        tornado.ioloop.IOLoop.instance().stop()
        logger.info("Exception whilst serving. Exiting")
        sys.exit()
        



