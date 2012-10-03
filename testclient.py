import socket

print "Creating client socket"
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect(('192.168.35.128', 61222))
testm = "LIVELOG!123test"
slen = client.send(testm)

rsp = client.recv(1024)

client.close()

print "Server responded: %s" % rsp

#LIVELOG!123test!192.168.35.128!42276
tokenized = rsp.split('!')

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.connect((tokenized[2], int(tokenized[3])))
client.send('L 10/02/2012 - 20:48:27: Log file started (file "logs/27175/L1002001.log") (game "/home/steam/srcds/orangebox/tf") (version "5072")')
client.close()
               

                      