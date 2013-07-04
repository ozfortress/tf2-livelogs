"""
The livelogs query queue library

This library allows the daemon to process a queue from the parser objects for database inserts
to increase performance and reduce concurrent database writes

This will also allow greater flow control of parser database insertions
"""

import threading

HIPRIO = 0 #high priority
NMPRIO = 1 #normal priority
LOPRIO = 2 #low priority

class query_queue(object):
    def __init__(self):
        self._last_queue_level = NMPRIO

        self.__queues = ( [], [], [] ) # tuple of lists for different queues

        self.__threading_lock = threading.Lock()


    def add_query(self, query_a, query_b=None, priority = NMPRIO):
        self.__threading_lock.acquire() #acquire a threading lock, so that other threads cannot add to the queue at the same time

        self.__add_query_to_queue((query_a, query_b), priority)

        self.__threading_lock.release() #release the lock, so the next thread blocked on acquiring the lock can have its turn

    def readd_query(self, query_tuple):
        #this will re-add a query to the queue at the last queue level
        self.__threading_lock.acquire()

        self.__add_query_to_queue(query_tuple, self._last_queue_level)

        self.__threading_lock.release()

    def __add_query_to_queue(self, query, priority):
        self.__queues[priority].append(query) #query is a tuple of two possible queries (i.e, insert/update for an upsert)
        #print "added query %s with priority %d" % (query, priority)
        print "length of queue %d: %d" % (priority, len(self.__queues[priority]))

    def get_next_query(self):
        """
        gets the next query to be run, by priority, so we look at the high priority queue first, 
        then proceed to low if no higher items were found

        We only get 1 query at a time, and pop it from the queue, as this method is called repeatedly
        by the queue thread, which will slowly wittle down the items in the queue
        """

        for queue_level, queue in enumerate(self.__queues): #queues tuple will always be in the same order
            if len(queue) > 0:
                #we have objects in this queue! pop the one at the front
                self._last_queue_level = queue_level
                return self.__pop_query(queue_level) #return the query and the priority, in case it must be added back to the queue

        #if we've reached this point, there was nothing in the queues, so return none
        return None

    def __pop_query(self, queue_index):
        self.__threading_lock.acquire() #lock while we pop

        rtn_query = self.__queues[queue_index].pop(0) #pop the first item in the queue

        self.__threading_lock.release()
        #print "popped %s at queue %d" % (rtn_query, queue_index)
        return rtn_query

    def queue_empty(self, queue_index):
        if len(self.__queues[queue_index]) > 0:
            return False #queue is not empty

        #queue is empty
        return True

    def copy(self):
        #shallow copy
        return self.__class__(self)



