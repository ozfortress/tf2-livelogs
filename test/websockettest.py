import websocket
import json
import threading
import urllib2
import time
import random

class wstestclient(object):
    def __init__(self, log_ident):
        self.ws = websocket.WebSocketApp("ws://192.168.35.128:61224/logupdate", on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)

        self.ws.on_open = self.on_open
        
        self.log_ident = log_ident

        self.done = False
        print "client ready for starting on log ident %s" % log_ident
        
    def on_message(self, sock, message):
        try:
            print "\n"
            print json.loads(message)
        except:
            print "RECEIVED: %s" % message
            print "error decoding json message"
            
    def on_error(self, sock, error):
        print "ERROR: %s" % error
        self.stop()

    def on_close(self, sock):
        print "WS closed"
        self.done = True

    def on_open(self, sock):
        print "Websocket opened. Let's send a log ident!"
        sock.send(json.dumps({"ident" : self.log_ident}))

    def stop(self):
        self.ws.close()
        self.done = True
        
    def start(self):
        print "STARTING WEBSOCKET CLIENT CONNECTION FOR LOG %s" % self.log_ident
        try:
            self.ws.run_forever()
        except:
            pass

if __name__ == "__main__":
    websocket.enableTrace(True)

    ll_api = urllib2.urlopen("http://192.168.106.128/api/main.php?action=get_live")

    api_data = json.load(ll_api)

    print "api data: %s" % api_data
    
    ll_api.close()

    clients = set()
    
    if "live" in api_data:
        for log_ident in api_data["live"]:
            print "establishing client for log ident %s" % log_ident

            client = wstestclient(log_ident)

            clients.add(client)

            client.thread = threading.Thread(target=client.start)
            client.thread.daemon = True
            client.thread.start()

            time.sleep(random.randint(1, 2))

        try:
            while len(clients) > 0:
                for client in clients.copy():
                    if client.done:
                        print "Client is done!"
                        clients.discard(client)
        except:
            for client in clients.copy():
                client.stop()
                
            quit()
    else:
        print "no live logs"