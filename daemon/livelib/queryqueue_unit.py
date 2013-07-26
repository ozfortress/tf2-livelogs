import queryqueue
import random
import threading
import gc
import time
import pdb
import logging

logging.basicConfig(level=logging.DEBUG, format="[(%(levelname)s) %(process)s %(asctime)s %(module)s:%(name)s:%(lineno)s] %(message)s", datefmt="%H:%M:%S")

queue = queryqueue.query_queue()


def populate_queue(maxrange = 500000):
    for i in xrange(0, maxrange):
        #print "adding to queue, i: %d" % i
        queue.add_query("SELECT FROM livelogs_player_stats WHERE steamid='76561198064565908' and class != 'UNKNOWN' group by class, kills, deaths order by deaths DESC, class ASC", priority = random.choice([queryqueue.NMPRIO, queryqueue.HIPRIO]))

#populate_queue(200000)

def pop_thread(queue_obj):
    while not queue_obj.queues_empty():
        for i in xrange(0, 2000):
            query_tuple = queue_obj.get_next_query()
            if not query_tuple:
                continue

            #print queue_obj.queue_length_all()


thread = threading.Thread(target=pop_thread, args=(queue,))
thread.daemon = True
#thread.start()

try:
    queue.serialise()
    print "serialised with queue lengths %s" % queue.queue_length_all()
    quit()
    while 1:
        print queue.queue_length_all()
        if queue.queues_empty():
            print gc.garbage
            gc.collect()

            print "ended"
            print queue.queue_length_all()
            pdb.set_trace()

except:
    #queue.serialise()
    pass