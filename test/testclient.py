import socket
import time
import threading

class testclient(object):
    def __init__(self):
        self.done = False
        self.stop = False

    def start(self, port):
        self.connect(port)
    
    def connect(self, portno):
        print "Creating client socket"
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            #client.connect(('119.15.97.230', 61222))
            client.connect(('192.168.35.128', 61222))
        except:
            client.close()
            return
     
        #testm = "LIVELOG!ADVENTUREBEWITHYOU!202.161.23.120!27015!cp_granary!JIMBOBJUNIOR3"
        testm = "LIVELOG!new_api_key!192.168.3.1!%(port)d!cp_granary!named_port_%(port)d!23142" % { "port": portno }
        slen = client.send(testm)

        portno += 1

        rsp = client.recv(1024)
     
        print "Server responded: %s" % rsp
        self.process_response(rsp)

    def process_response(self, rsp):
        #LIVELOG!123test!192.168.35.128!42276!UNIQUE_IDENT OR REUSE
        tokenized = rsp.split('!')
        #LIVELOG!123test!192.168.35.128!57221!3232244481_27015_1358162178
        if (len(tokenized) == 5):
            if (tokenized[4] != "REUSE"):
                client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                client.connect((tokenized[2], int(tokenized[3])))

                #client.send('L 10/01/2012 - 21:38:34: "Liquid\'zato<46><STEAM_0:0:42607036><Blue>" killed "[v3] Faithless<47><STEAM_0:0:52150090><Red>" with "tf_projectile_rocket" (attacker_position "-1158 -194 295") (victim_position "-1200 197 308")')

                log_file = open(r'E:\Git\livelogs\test\test_log.log')

                x = 0

                for logline in log_file:
                    if self.stop:
                        break
                    
                    line = logline.lstrip("\xFF").lstrip("R").rstrip()
                    #line = logline.lstrip("\xFF").rstrip()
                    #print line
                    sendline = "S%s%s\r\n" % ("new_api_key", line)

                    """total_sent = 0
                    while total_sent < len(sendline):
                        sent = client.send(sendline[total_sent:])
                        if sent == 0:
                            break
                        
                        total_sent += sent
                    """
                    client.sendall(sendline)
                    #client.send("R%s\r\n" % line)
                        
                    x += 1
                    time.sleep(0.1)

                log_file.close()

                client.close()        
            else:
                print "livelogs daemon told us to re-use... don't want to do that with test client!"
        else:
            print "Invalid response"

        self.done = True
        print "done"

def do_threads():
    clients = set()

    for i in range(0,1):
        portno = 20000 + i

        client = testclient()

        clients.add(client)

        client.thread = threading.Thread(target=client.start, args=(portno,))
        client.thread.daemon = True

        time.sleep(2)
        client.thread.start()
    try:
        while len(clients) > 0:
            for client in clients.copy():
                if client.done:
                    print "Client is done!"
                    clients.discard(client)
    except:
        for client in clients.copy()
            client.stop = True
            
        quit()
    
do_threads()
