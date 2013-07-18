import threading
import logging

"""
Holds all data related to websocket clients for the livelogs websocket server

This includes clients that aren't added to valid log idents yet, and clients that are

"""

class log_data(object):
	def __init__(self, log_cache, log_cache_lock):
		self.log_cache = log_cache

		self.__valid_clients = {}

		self.__invalid_clients = {}

		self.__cache_lock = log_cache_lock #a lock for operations on the log cache, passed down
		self.__invalid_client_lock = threading.Lock() #a lock for operations on invalid_clients
		self.__valid_client_lock = threading.Lock() #a lock for any operations on log_data

	def add_client(self, client_obj, cache_valid=False):
		#masks __add_invalid_client and __add_valid_client

		if not client_obj._log_ident:
			logging.error("Cannot add client that doesn't have a log ident")
			return
		
		clog_ident = client_obj._log_ident

		if cache_valid:
			self.__valid_client_lock.acquire()

		elif clog_ident in self.__log_data:
			self.__add_valid_client(client_obj)

		else:
			#invalid
			self.__invalid_client_lock.acquire()

			self.__add_invalid_client(client_obj)

			self.__invalid_client_lock.release()
		

		self.__valid_client_lock.release()

	def __add_valid_client(self, client_obj):
		log_ident = client_obj._log_ident

		if log_ident in self.__log_data:
			self.__log_data[log_ident].add(client_obj)

		else:
			#create new entry
			self.__log_data[log_ident] = set(client_obj)


	def __add_invalid_client(self, client_obj):
		

	def _get_log_cache(self, log_ident):


	def get_invalid_idents(self):
		#returns a list of log idents that are considered invalid (ie, in the invalid_clients dict)
		il = []

		self.__invalid_client_lock.acquire()
		
		for log_ident in self.__invalid_clients:
			il.append(log_ident)

		self.__invalid_client_lock.release()

		return il



