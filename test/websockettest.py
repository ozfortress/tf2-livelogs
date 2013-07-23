import websocket
import json

def on_message(sock, message):
    try:
        print "\n"
        print json.loads(message)
    except:
        print "RECEIVED: %s" % message
        print "error decoding json message"
        
def on_error(sock, error):
    print "ERROR: %s" % error

def on_close(sock):
    print "WS closed"

def on_open(sock):
    print "Websocket opened. Let's send a log ident!"
    sock.send(json.dumps({"ident" : "3232244481_20000_1374565435"}))

if __name__ == "__main__":
    websocket.enableTrace(True)

    ws = websocket.WebSocketApp("ws://192.168.35.128:61224/logupdate", on_message=on_message, on_error=on_error, on_close=on_close)
    ws.on_open = on_open
    try:
        ws.run_forever()
    except:
        quit()