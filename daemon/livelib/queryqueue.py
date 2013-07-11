"""
The livelogs query queue library

This library allows the daemon to process a queue from the parser objects for database inserts
to increase performance and reduce concurrent database writes

This will also allow greater flow control of parser database insertions
"""

import threading
import collections

HIPRIO = 0 #high priority
NMPRIO = 1 #normal priority
LOPRIO = 2 #low priority

class query_queue(object):
    def __init__(self):
        self._last_queue_level = NMPRIO

        self.__queue_levels = (HIPRIO, NMPRIO, LOPRIO)

        self.__queues = {} # dict of queues, which is populated on the fly

        #populate the queues dict str8 up
        #for queue_level in self.__queue_levels:
        #    self.__allocate_empty_queue(queue_level) 

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
        if priority in self.__queues:
            #if the queue exists, append to it
            self.__queues[priority].append(query) #query is a tuple of two possible queries (i.e, insert/update for an upsert)
        else:
            #else, create the queue and append to it
            self.__allocate_empty_queue(priority) #re-allocate the deleted queue
            self.__queues[priority].append(query)

        #print "added query %s with priority %d" % (query, priority)
        #print "length of queue %d: %d" % (priority, len(self.__queues[priority]))

    def get_next_query(self):
        """
        gets the next query to be run, by priority, so we look at the high priority queue first, 
        then proceed to low if no higher items were found

        We only get 1 query at a time, and pop it from the queue, as this method is called repeatedly
        by the queue thread, which will slowly wittle down the items in the queue
        """

        for queue_level in self.__queue_levels: #queues tuple will always be in the same order
            if queue_level in self.__queues: #make sure the queue hasn't been deleted
                if len(self.__queues[queue_level]) > 0:
                    #we have objects in this queue! pop the one at the front
                    self._last_queue_level = queue_level

                    return self.pop_query(queue_level) #return the query and the priority, in case it must be added back to the queue
                else:
                    #the queue is empty and needs to be freed
                    self.__free_empty_queue(queue_level)
                
        #if we've reached this point, there was nothing in the queues, so return none
        return None

    def pop_query(self, queue_index):
        #non-private wrapper for __pop_query, which performs threading locks to prevent side-by-side access
        self.__threading_lock.acquire() #lock while we pop

        rtn_query = self.__pop_query(queue_index)

        self.__threading_lock.release()

        return rtn_query

    def __pop_query(self, queue_index):
        return self.__queues[queue_index].popleft() #pop the first item in the queue

    def __allocate_empty_queue(self, queue_index):
        #normally we'd lock this, but it is only called inside __add_query_to_queue, which already has a lock around it
        if queue_index not in self.__queues:
            self.__queues[queue_index] = collections.deque()

    
    def __free_empty_queue(self, queue_index):
        """
        if a queue is empty, we free it so that the memory is deallocated

        normally we'd have a non-private function and perform the thread locks in there, but since we only want
        the object to be able to free the queues, we'll just leave the locks in here for this one
        """
        self.__threading_lock.acquire()

        del self.__queues[queue_index]

        self.__threading_lock.release()

    def queues_empty(self):
        for queue in self.__queues:
            if len(queue) > 0:
                return False

        #queues are empty
        return True

    def queue_length(self, queue_index):
        if queue_index in self.__queues:
            return len(self.__queues[queue_index])
        else:
            return 0

    def queue_length_all(self):
        rtn = []
        for queue_level in self.__queue_levels:
            if queue_level in self.__queues:
                rtn.append(len(self.__queues[queue_level]))
            else:
                rtn.append("NaN")

        return rtn


    def copy(self):
        #shallow copy
        return self.__class__(self)



