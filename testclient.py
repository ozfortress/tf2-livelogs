import socket

print "Creating client socket"
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

client.connect((192.168.35.128, 38113))
testm = "TESTING 123"
slen = client.send(testm)

rsp = client.recv(slen)

print "Server responded: %s" % rsp

