import threading
import logging
import collections

"""
Holds all data related to websocket clients for the livelogs websocket server

This includes clients that aren't added to valid log idents yet, and clients that are

"""

class client_data(object):
    def __init__(self):
        self.__valid_clients = {}
        self.__invalid_clients = {}

        self.__invalid_client_lock = threading.Lock() #a lock for operations on invalid_clients
        self.__valid_client_lock = threading.Lock() #a lock for any operations on log_data

    def add_client(self, client_obj, cache_valid=False):
        #masks __add_invalid_client and __add_valid_client

        added_valid = False

        if not client_obj._log_ident:
            logging.error("Cannot add client that doesn't have a log ident")
            return None
        
        clog_ident = client_obj._log_ident

        self.__get_valid_lock()
        self.__get_invalid_lock()

        if cache_valid or (clog_ident in self.__valid_clients):
            #valid cache, or the log ident is in the valid clients dict, so just add straight to the valid clients
            self.__add_valid_client(client_obj)
            added_valid = True

        else:
            #invalid, or unknown, so just add to invalid clients & wait for the server thread to move the client, or delete it
            self.__add_invalid_client(client_obj)

        self.__release_valid_lock()
        self.__release_invalid_lock()

        return added_valid

    def __add_valid_client(self, client_obj):
        log_ident = client_obj._log_ident

        logging.info("adding valid client to ident %s", log_ident)

        if log_ident in self.__valid_clients:
            self.__valid_clients[log_ident].add(client_obj)

        else:
            #create new entry
            self.__valid_clients[log_ident] = set()
            self.__valid_clients[log_ident].add(client_obj)


    def __add_invalid_client(self, client_obj):
        log_ident = client_obj._log_ident

        logging.info("adding invalid client to ident %s", log_ident)

        if log_ident in self.__invalid_clients:
            self.__invalid_clients[log_ident].add(client_obj)

        else:
            self.__invalid_clients[log_ident] = set()
            self.__invalid_clients[log_ident].add(client_obj)

    def delete_client(self, client_obj):
        #delete the client from whatever dict he is in, if the client actually has a log ident
        log_ident = client_obj._log_ident

        if not log_ident:
            logging.error("Cannot delete a client that doesn't have a log ident")
            return False

        #check valid first, because it's probs the most likely case
        self.__get_valid_lock()
        if log_ident in self.__valid_clients:
            self.__valid_clients[log_ident].discard(client_obj)

        self.__release_valid_lock()

        self.__get_invalid_lock()
        if log_ident in self.__invalid_clients:
            self.__invalid_clients[log_ident].discard(client_obj)

        self.__release_invalid_lock()


    def delete_ident(self, log_ident):
        #deletes an ident and associated clients
        self.__get_valid_lock()
        if log_ident in self.__valid_clients:
            self.__delete_clients(self.__valid_clients[log_ident])

            del self.__valid_clients[log_ident]

        self.__release_valid_lock()

        self.__get_invalid_lock()
        if log_ident in self.__invalid_clients:
            self.__delete_clients(self.__invalid_clients[log_ident])

            del self.__invalid_clients[log_ident]

        self.__release_invalid_lock()


    def __delete_clients(self, client_set):
        for client in client_set.copy():
            client_set.discard(client)


    def move_invalid_ident(self, log_ident):
        #moves an invalid ident to the valid dict, this is for when another thread checks the status and confirms the log is valid
        self.__get_valid_lock()
        self.__get_invalid_lock()

        if not (log_ident in self.__invalid_clients):
            logging.error("Log ident does not exist in invalid, so it cannot be moved")
            self.__release_valid_lock()
            self.__release_invalid_lock()

            return


        if log_ident in self.__valid_clients:
            #key is already in valid log idents for some reason... let us merge this shit
            for client in self.__invalid_clients[log_ident]:
                self.__valid_clients[log_ident].add(client)

        else:
            self.__valid_clients[log_ident] = self.__invalid_clients[log_ident]

        
        del self.__invalid_clients[log_ident] #finally, delete the key from invalid client dict

        self.__release_valid_lock()
        self.__release_invalid_lock()


    def get_invalid_idents(self):
        #returns a list of log idents that are considered invalid (ie, in the invalid_clients dict)
        il = []

        self.__get_invalid_lock()
        
        for log_ident in self.__invalid_clients:
            il.append(log_ident)

        self.__release_invalid_lock()

        logging.debug("Invalid clients: %s", il)
        
        return il


    def get_valid_idents(self):
        self.__get_valid_lock()

        vl = []

        for log_ident in self.__valid_clients:
            vl.append(log_ident)

        self.__release_valid_lock()

        logging.debug("Valid clients: %s", vl)

        return vl

    def get_idents(self):
        #gets all idents, invalid and valid
        self.__get_valid_lock()
        self.__get_invalid_lock()
        ident_list = []

        for log_ident in self.__valid_clients:
            ident_list.append(log_ident)


        for log_ident in self.__invalid_clients:
            ident_list.append(log_ident)

        self.__release_valid_lock()
        self.__release_invalid_lock()

        return ident_list


    def log_ident_valid(self, log_ident):
        self.__get_valid_lock()

        valid = False

        if log_ident in self.__valid_clients:
            valid = True

        self.__release_valid_lock()

        return valid

    def log_ident_invalid(self, log_ident):
        self.__get_invalid_lock()

        invalid = False

        if log_ident in self.__invalid_clients:
            invalid = True

        self.__release_invalid_lock()

        return invalid

    def get_num_vclients(self, log_ident):
        #returns the number of valid clients associated with the log ident

        self.__get_valid_lock()

        if log_ident in self.__valid_clients:
            nc = len(self.__valid_clients[log_ident])

        else:
            nc = 0

        self.__release_valid_lock()

        return nc

    def get_num_ivclients(self, log_ident):
        self.__get_invalid_lock()

        if log_ident in self.__invalid_clients:
            nc = len(self.__invalid_clients[log_ident])

        else:
            nc = 0

        self.__release_invalid_lock()

        return nc

    def get_vclients(self, log_ident):
        #returns the clients associated with the valid log ident
        self.__get_valid_lock()

        clients = None

        if log_ident in self.__valid_clients:
            clients = self.__valid_clients[log_ident]

        self.__release_valid_lock()

        return clients

    def get_ivclients(self, log_ident):
        #returns the invalid clients associated with the log ident
        self.__get_invalid_lock()

        clients = None        

        if log_ident in self.__invalid_clients:
            clients = self.__invalid_clients[log_ident]

        self.__release_invalid_lock()

        return clients

    def __get_valid_lock(self):
        try:
            logging.debug("Getting valid lock")
            self.__valid_client_lock.acquire()
        except:
            pass

    def __release_valid_lock(self):
        try:
            logging.debug("Releasing valid lock")
            self.__valid_client_lock.release()
        except:
            pass

    def __get_invalid_lock(self):
        try:
            logging.debug("Getting invalid lock")
            self.__invalid_client_lock.acquire()
        except:
            pass

    def __release_invalid_lock(self):
        try:
            logging.debug("Releasing invalid lock")
            self.__invalid_client_lock.release()
        except:
            pass

"""
Manager data object, to hold db managers and provide ez access functions

"""


class manager_data(object):
    def __init__(self):
        self.__managers = collections.deque()

    def add_manager(self, manager_tuple):
        #add the manager tuple in the form (log_ident, manager) to the left of the deque
        self.__managers.appendleft(manager_tuple)

    def get_manager(self, log_ident):
        #get the db manager object corresponding to the log ident
        for manager_ident, manager in self.__managers:
            if manager_ident == log_ident:
                return manager

        return None

    def __len__(self):
        return len(self.__managers)

    def __contains__(self, item):
        return self.__manager_exists(item)

    def exists(self, log_ident):
        return self.__manager_exists(log_ident)

    def __manager_exists(self, log_ident):
        #loop over the deque to see if this db manager exists or not
        for manager_data in self.__managers:
            if manager_data[0] == log_ident:
                return True

        return False

    def delete_manager(self, log_ident):
        for manager_data in self.__managers:
            if manager_data[0] == log_ident:
                self.__managers.remove(manager_data)
                break

    def cycle(self):
        #cycles the db managers, by moving the first manager to the end
        #return the db manager that was moved to the end, so updates can be performed on it

        manager_ident, manager = self.__managers.popleft()

        self.__managers.append((manager_ident, manager))

        return manager

