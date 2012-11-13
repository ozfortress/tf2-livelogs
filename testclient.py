import socket
import time
 
print "Creating client socket"
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    client.connect(('119.15.97.230', 61222))
except:
    quit()
 
#testm = "LIVELOG!123test!124.148.180.174!27015!cp_granary!John"
testm = "LIVELOG!123test!192.168.35.1!27015!cp_granary!John"
slen = client.send(testm)

rsp = client.recv(1024)

client.close()
 
print "Server responded: %s" % rsp
 
#LIVELOG!123test!192.168.35.128!42276!UNIQUE_IDENT OR REUSE
tokenized = rsp.split('!')

if (len(tokenized) <= 5):
    if (tokenized[4] != "REUSE"):
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.connect((tokenized[2], int(tokenized[3])))

        log_file = open(r'E:\Git\livelogs\test_log.log')

        for logline in log_file:
            print logline
            client.send(logline)

            time.sleep(0.02)

        log_file.close()

        client.close()
        
    else:
        print "livelogs daemon told us to re-use... don't want to do that with test client!"
else:
    print "Invalid response"