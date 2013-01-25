import socket
import time
 
print "Creating client socket"
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    #client.connect(('119.15.97.230', 61222))
    client.connect(('192.168.35.128', 61222))
except:
    quit()
 
#testm = "LIVELOG!123test!124.168.96.208!27015!cp_granary!JIMBOBJUNIOR3"
testm = "LIVELOG!123test!192.168.35.1!27015!cp_granary!new name here!23142"
slen = client.send(testm)

rsp = client.recv(1024)

#client.close()
 
print "Server responded: %s" % rsp

#LIVELOG!123test!192.168.35.128!42276!UNIQUE_IDENT OR REUSE
tokenized = rsp.split('!')
#LIVELOG!123test!192.168.35.128!57221!3232244481_27015_1358162178
if (len(tokenized) <= 5):
    if (tokenized[4] != "REUSE"):
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #client.connect(("192.168.35.128", 57221))
        client.connect((tokenized[2], int(tokenized[3])))

        #client.send('L 10/01/2012 - 21:38:34: "Liquid\'zato<46><STEAM_0:0:42607036><Blue>" killed "[v3] Faithless<47><STEAM_0:0:52150090><Red>" with "tf_projectile_rocket" (attacker_position "-1158 -194 295") (victim_position "-1200 197 308")')

        log_file = open(r'E:\Git\livelogs\test\test_log.log')
        
        for logline in log_file:
            print logline
            client.send(logline)

            time.sleep(0.05)

        log_file.close()

        client.close()
        
    else:
        print "livelogs daemon told us to re-use... don't want to do that with test client!"
else:
    print "Invalid response"