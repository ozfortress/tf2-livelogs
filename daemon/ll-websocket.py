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
from livelib import ws_data

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
        
        self.__db_managers = ws_data.ManagerData() #a manager_data object that will manage db manager data!

        self.log_cache = [] #holds a set of tuples containing log idents, the last time they were updated, and the status (live/not live) | [(cache_time, log_ident, status<t/f>), (cache_time, log_ident, status<t/f>)]

        self.clients = ws_data.ClientData() #a client_data object, which contains all valid/invalid clients

        self._sending_timer = tornado.ioloop.PeriodicCallback(self.__send_log_updates, self.update_rate * 1000)
        self._sending_timer.start()

        self._status_update_timer = tornado.ioloop.PeriodicCallback(self.__process_log_status, self.update_rate * 1000)
        self._status_update_timer.start()

        self._db_update_timer = tornado.ioloop.PeriodicCallback(self.__get_dbmanager_updates, 1000) #round robin the managers every 1s
        self._db_update_timer.start()

        self.database_lock = threading.Lock() #a lock that is passed down to the db managers. this will prevent multiple db managers from trying to get status at the same time

        tornado.web.Application.__init__(self, handlers, **settings)
            
    def add_to_cache(self, log_ident, status):
        self.log_cache.append((int(round(time.time())), log_ident, status))

    def remove_from_cache(self, cache_item):
        self.log_cache.remove(cache_item)

    def update_cache(self, log_ident, status):
        #updates the status of a log ident
        for log_cache in self.log_cache:
            if log_ident == log_cache[1]:
                self.remove_from_cache(log_cache)
                break

        self.add_to_cache(log_ident, status)

    def clean_cache(self):
        #removes expired cache items
        self.logger.info("Cleaning cache...")

        time_ctime = int(round(time.time()))
        list_copy = list(self.log_cache)

        for log_cache in list_copy:
            time_diff = time_ctime - int(log_cache[0])

            if log_cache[2] == False:
                expiry_threshold = 600
            else:
                expiry_threshold = 60

            if time_diff > expiry_threshold:
                self.remove_from_cache(log_cache)
        
        del list_copy #delete the copied list


    def get_log_cache(self, log_ident):
        #return a cache only if the cache is valid

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
                    self.remove_from_cache(log_cache)
                    break

                else:
                    rtn = log_cache

        return rtn

    def add_client(self, client_obj):
        log_ident = client_obj._log_ident

        if not log_ident:
            self.logger.debug("Client attempted adding without a log ident??")
            client_obj.close()

            return

        log_cache = self.get_log_cache(log_ident)

        if not log_cache:
            #we're unsure if this log is valid
            add_res = self.clients.add_client(client_obj)
            
            if add_res == True:
                #log was not cached, but the client was added to a valid log ident. therefore, the log is still valid and should be re-added to the cache as such
                self.add_to_cache(log_ident, True)
                client_obj.write_message("LOG_IS_LIVE")

            #else, the client was added to the invalid list which will be checked by the status threa

        else:
            #we know the log is valid, so we can check the live status
            if log_cache[2] == True:
                self.clients.add_client(client_obj, cache_valid = True)
                client_obj.write_message("LOG_IS_LIVE")

            else:
                #log is not live, disconnect the client
                client_obj.disconnect_not_live()

    def delete_client(self, client_obj):
        self.logger.debug("Deleting client")
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
                    client.disconnect_invalid()

        self.clients.delete_ident(log_ident)

    def add_dbmanager(self, log_ident, tstamp):
        if log_ident not in self.__db_managers:
            #add the db manager to the left of the queue, so that it gets updates next turn
            self.__db_managers.add_manager((log_ident, self.__new_dbmanager(log_ident, tstamp)))

    def __new_dbmanager(self, log_ident, tstamp):
        #creates a new db manager object and returns it
        return dbmanager.dbManager(self.db, log_ident, self.database_lock, self.update_rate, tstamp)

    def __end_log(self, log_ident):
        #deletes a db manager and associated clients
        end_update_dict = None

        if log_ident in self.__db_managers:
            manager = self.__db_managers.get_manager(log_ident)

            end_update_dict = manager.full_update()

            manager.cleanup()

            self.__db_managers.delete_manager(log_ident)

        clients = self.clients.get_vclients(log_ident)
        if clients:
            for client in clients:
                client.disconnect_end(end_update_dict)

        self.clients.delete_ident(log_ident)

        self.update_cache(log_ident, False)

    def __get_dbmanager_updates(self):
        #cyclicly update db managers, 1 per periodic callback (i.e round robin queue)
        
        #self.logger.debug("Getting DB Manager updates")
        if len(self.__db_managers) > 0:
            cycle_manager = self.__db_managers.cycle()

            cycle_manager.get_database_updates()

    def __send_log_updates(self):
        valid_idents = self.clients.get_valid_idents()
        num_idents = len(valid_idents)

        self.logger.info("Sending updates. Number of active logs: %d", num_idents)

        if num_idents == 0:
            return

        try:
            for log_id in valid_idents:
                if self.clients.get_num_vclients(log_id) == 0:
                    continue

                if log_id in self.__db_managers:
                    log_manager = self.__db_managers.get_manager(log_id)

                else:
                    #no log manager exists for this... how & why?
                    self.logger.error("log %s has clients and is considered valid, but has no db manager?")
                    continue

                delta_update_dict = log_manager.compressed_update()
                full_update_dict = {}

                #self.logger.debug("Got update dict for %s: %s", log_id, delta_update_dict)

                for client in self.clients.get_vclients(log_id):
                    #client is a websocket client object, which data can be sent to using client.write_message, etc
                    #client.write_message("HELLO!")
                    if not client.HAD_FIRST_UPDATE:
                        #need to send complete values on first update to keep clients in sync with the server
                        if not full_update_dict:
                            full_update_dict = log_manager.full_update()

                        #send a complete update to the client
                        client.write_message(full_update_dict)
                    
                        client.HAD_FIRST_UPDATE = True

                    else:
                        if delta_update_dict: #if the dict is not empty, send it. else, just keep processing and waiting for new update
                            self.logger.debug("Sending update to client %s", client.cip)
                            client.write_message(delta_update_dict)
        except:
            self.logger.exception()

    def _log_finished_callback(self, log_ident):
        self.logger.info("Log id %s is over. Closing connections", log_ident)
        self.__end_log(log_ident)

    def __process_log_status(self):
        self.logger.info("Getting log status")
        try:
            self.clean_cache()

            self._status_invalid_idents = self.clients.get_invalid_idents() #a list of log idents in the invalid dict
            self._status_valid_idents = self.__db_managers.get_idents()
            
            log_idents = self._status_invalid_idents + self._status_valid_idents
            self.logger.debug("Current log idents: %s", log_idents)

            if len(log_idents) == 0:
                self.logger.debug("No log idents present to check status for")

                return

            #create a select statement to get status of all log idents in the queue
            filter_string = ""

            for log_ident in log_idents:
                if len(filter_string) > 0:
                    filter_string += " OR "

                filter_string += "log_ident = E'%s'" % (log_ident)

            select_query = "SELECT log_ident, live, tstamp FROM livelogs_log_index WHERE (%s)" % (filter_string)

            self.logger.debug("status query: %s", select_query)

            try:
                self.db.execute(select_query, callback = self._status_callback)
            except:
                self.logger.exception("Exception executing status query")

        except:
            self.logger.exception("Exception getting status")
    
    def _status_callback(self, cursor, error):
        if error:
            self.logger.error("Error querying database for log status")

            return

        #if live is NOT NULL, then the log exists
        #live == t means the log is live, and live == f means it's not live
        self.logger.info("Processing log status results")

        results = cursor.fetchall() #fetchall returns a list of tuples of all results
        
        self.logger.debug("results: %s", results)

        if results and len(results) > 0:
            for log_status in results: #log_status is a tuple in form (log_ident, live, tstamp)
                #self.logger.debug("log_status tuple: %s", log_status)
                log_ident, live, tstamp = log_status

                self.add_to_cache(log_ident, live)
                """
                 if the log is live, we check if its in the invalid/valid dicts
                   if in the invalid dict, the ident and associated clients get updated to
                   live idents
                
                   if in the valid dict, the ident is simply removed from the temporary dict

                 if the log is not live, we check if it's in the valid dict
                   if in the valid dict, the log is no longer live, so we can send a final
                   update and close all client connections and the dbmanager

                   else, the ident is unknown (definitely invalid) and we close it and
                   associated clients

                 after these checks, we close whatever idents are remaining because
                 the idents no longer exist, or never existed
                    i.e if a log was empty and deleted after the timeout, it would
                    still be considered valid by this daemon and never invalid via
                    the normal check. therefore, we must close all left over idents
                    after a status check
                """

                if live == True:
                    self.logger.debug("log %s is live", log_ident)

                    if log_ident in self._status_invalid_idents:
                        #move the queue to the dict of valid log idents
                        self.add_live_ident(log_ident, tstamp)

                    elif log_ident in self._status_valid_idents:
                        # log ident is valid and live, so we can remove it from the temp dict
                        self._status_valid_idents.remove(log_ident)
                    
                else:
                    self.logger.debug("log %s is not live, disconnecting clients", log_ident)

                    if log_ident in self._status_valid_idents:
                        #valid ident is no longer live, close it
                        self._log_finished_callback(log_ident) #run the ending callback
                        self._status_valid_idents.remove(log_ident)

                    else:
                        #unknown ident is not live
                        self.close_invalid(log_ident, not_live = True)

                #remove the log ident, because it's clearly not invalid
                if log_ident in self._status_invalid_idents:
                    self._status_invalid_idents.remove(log_ident)


        # if idents are still in the invalid dict... delete 
        # them because they are actually invalid and do not exist
        for log_ident in self._status_invalid_idents:
            self.logger.info("Log %s is definitely invalid (no query result). Deleting", log_ident)
            self.close_invalid(log_ident)

        # left over valid idents because the ident was deleted due
        # to an empty log. end these logs
        for log_ident in self._status_valid_idents:
            self.logger.info("Log %s is a zombie log (valid, but no status result). Deleting", log_ident)
            self.__end_log(log_ident)


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
            self.write_message("LOG_END")

            if end_update:
                self.write_message(end_update)

            self.close()

    def disconnect_invalid(self):
        self.disconnect_not_live()

            
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
    
    ioloop = tornado.ioloop.IOLoop.instance()

    llWebSocketServer = llWSApplication(update_rate = tornado.options.options.update_rate)
        
    llWebSocketServer.db = momoko.Pool(
            dsn = db_details,
            minconn = 2, #minimum number of connections for the momoko pool to maintain
            maxconn = 6, #max number of conns that will be opened
            cleanup_timeout = 5, #how often (in seconds) connections are closed (cleaned up) when number of connections > minconn
        )
    
    llWebSocketServer.listen(tornado.options.options.port, tornado.options.options.ip)
    logger.info("Websocket server listening on %s:%s", tornado.options.options.ip, tornado.options.options.port)
    
    try:
        ioloop.start()
    except:
        llWebSocketServer.db.close()
        tornado.ioloop.IOLoop.instance().stop()
        logger.info("Exception whilst serving. Exiting")
        sys.exit()
        



