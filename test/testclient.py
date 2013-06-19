import socket
import time

def connect():
    print "Creating client socket"
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        #client.connect(('119.15.97.230', 61222))
        client.connect(('192.168.35.128', 61222))
    except:
        quit()
 
    #testm = "LIVELOG!ADVENTUREBEWITHYOU!202.161.23.120!27015!cp_granary!JIMBOBJUNIOR3"
    testm = "LIVELOG!new_api_key!192.168.3.1!27015!cp_granary!newer name here!23142"
    slen = client.send(testm)

    rsp = client.recv(1024)
 
    print "Server responded: %s" % rsp
    process_response(rsp)

def process_response(rsp):
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

            x = 0

            for logline in log_file:
                line = logline.lstrip("\xFF").lstrip("R").rstrip()
                if line:
                    #client.send("S%s%s" % ("new_api_key", line))
                    client.send(line)

                """if x is 100:
                    client.send('L 10/01/2012 - 21:38:34: "LIVELOG_GAME_RESTART"')

                    break
                """
                x += 1
                time.sleep(0.01)

            log_file.close()

            client.close()

            #connect()
            
            
        else:
            print "livelogs daemon told us to re-use... don't want to do that with test client!"
    else:
        print "Invalid response"

connect()