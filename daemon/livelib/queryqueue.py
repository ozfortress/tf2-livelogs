"""
The livelogs query queue library

This library allows the daemon to process a queue from the parser objects for database inserts
to increase performance and reduce concurrent database writes

This will also allow greater flow control of parser database insertions
"""

import threading

class query_queue(object):
    def __init__(self):
        self.__queue_levels = ["high", "normal", "low"]

        self.__queue_priority = {
            "high": 0,
            "normal": 1,
            "low": 2
        } #a priority queue for queries

        self.__queue = ( [], [], [] ) # tuple of lists for different queues

        self.__threading_lock = threading.Lock()

    def add_query(self, query_a, query_b, priority = "normal"):
        self.__threading_lock.acquire() #acquire a lock on the add_query function, so that threads cannot add to the queue at the same time

        self._add_query_to_queue((query_a, query_b), self.__queue_priority[priority])

        self.__threading_lock.release() #release the lock

    def _add_query_to_queue(self, query, priority):
        self.__queue[priority].append(query) #query is a tuple of two possible 'queries' (i.e, insert/update for an upsert)

    def get_next_query(self):
        """
        gets the next query to be run, by priority

        so we look at the high priority queue first, then proceed to low if no higher items were found
        """

        for queue_level in self.__queue_levels: #list will always be in the same order
            queue = self.__queue[self.__queue_priority[queue_level]]
            if len(queue) > 0:
                #we have objects in this queue! pop the one at the front
                self._pop_query


    def _pop_query(self, queue):

    def copy(self):
        #shallow copy
        return self.__class__(self)

