import psycopg2
import time
import struct
import socket
import re
from pprint import pprint

class parserClass():
    def __init__(self, server_address, ipgnBooker=None):
        if (ipgnBooker != None):
            self.bNamedLog = True
            self.namedLogName = ipgnBooker

        
        self.serverSendingLogs = server_address

        self.UNIQUE_IDENT = str(self.ip2long(server_address[0])) + "_" + str(server_address[1]) + "_" + str(int(round(time.time())))

        print "PARSER UNIQUE IDENT: " + self.UNIQUE_IDENT
        

        try:
            self.psqlConn = psycopg2.connect(host="localhost", port="5432", database="livelogs", user="livelogs", password="hello")
    
        except Exception, e:
            print "Had exception while trying to connect to psql database: " + e.pgerror

        
        self.dbCursor = self.psqlConn.cursor()
        
        self.dbCursor.execute("SELECT create_global_stat_table()")
        self.dbCursor.execute("SELECT setup_log_tables(%s)", (self.UNIQUE_IDENT,))

        self.psqlConn.commit()

        self.EVENT_TABLE = "log_event_" + self.UNIQUE_IDENT
        self.STAT_TABLE = "log_stat_" + self.UNIQUE_IDENT
        self.KILL_TABLE = "log_kill_" + self.UNIQUE_IDENT
        self.CHAT_TABLE = "log_chat_" + self.UNIQUE_IDENT
        self.ROUND_TABLE = "log_round_" + self.UNIQUE_IDENT

        self.dbCursor.close()
        self.psqlConn.close()

        print "Parser initialised"

    def ip2long(self, ip):
        print "ip2long ip: " + ip
        return struct.unpack('!L', socket.inet_aton(ip))[0]

    def long2ip(self, longip):
        return socket.inet_ntoa(struct.pack('L', longip))


    def parse(self, logdata):
        if not logdata:
            return

        print "PARSING LOG: %s" % logdata

        regex = self.regex #avoid having to use fucking self.regex every time (ANNOYING++++)
        regml = self.regml #local def for regml ^^^


        #if (res):
        #    print "Matching regex:"
        #    pprint(res.groups())

        #log file start
        #RL 10/07/2012 - 01:13:34: Log file started (file "logs_pug/L1007104.log") (game "/games/tf2_pug/orangebox/tf") (version "5072")
        res = regex(r"L (\S+) - (\S+) Log file started \x28file \"(.*?)\"\x29", logdata)
        if (res):
            print "Log file started"
            pprint(res.groups())
            ##do shit with log file name?
            
            return

        #log time
        res = regex(r'L (\S+) - (\S+):', logdata)
        if (res):
            print "Time of current log"
            pprint(res.groups())
            

        #damage dealt
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "damage" \x28damage "(\d+)"\x29', logdata)
        if (res):
            print "Damage dealt"
            pprint(res.groups())
            #('[v3] Kaki', '51', 'STEAM_0:1:35387674', 'Red', '40')
            sid = regml(res, 3)
            name = regml(res, 1)
            dmg = regml(res, 5)

            #query = "INSERT INTO %s 
            
            return

        #healing done
        #"vsn.RynoCerus<6><STEAM_0:0:23192637><Blue>" triggered "healed" against "Hyperbrole<3><STEAM_0:1:22674758><Blue>" (healing "26")
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "healed" against "(.*)<(\d+)><(.*)><(Red|Blue)>" \x28healing "(\d+)"\x29', logdata)
        if (res):
            print "Healing done"
            pprint(res.groups())

            return

        #item picked up
        #"skae<14><STEAM_0:1:31647857><Red>" picked up item "ammopack_medium"
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" picked up item "(.*)"', logdata)
        if (res):
            print "Item picked up"
            pprint(res.groups())
        
            return

        #player killed (normal)
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" killed "(.*)<(\d+)><(.*)><(Red|Blue)>" with "(.*)" \x28attacker_position "(.*)"\x29 \x28victim_position "(.*)"\x29', logdata)
        if (res):
            print "Player killed (normal kill)"
            pprint(res.groups())

            return

        #player killed (special kill) 
        #"Liquid'Time<41><STEAM_0:1:19238234><Blue>" killed "[v3] Roight<53><STEAM_0:0:8283620><Red>" with "knife" (customkill "backstab") (attacker_position "-1085 99 240") (victim_position "-1113 51 240")
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" killed "(.*)<(\d+)><(.*)><(Red|Blue)>" with "(.*)" \x28customkill "(.*)"\x29 \x28attacker_position "(.*)"\x29 \x28victim_position "(.*)"\x29', logdata)
        if (res):
            print "Player killed (customkill)"
            pprint(res.groups())

            return
        
        #player assist
        #"Iyvn<40><STEAM_0:1:41931908><Blue>" triggered "kill assist" against "[v3] Kaki<51><STEAM_0:1:35387674><Red>" (assister_position "-905 -705 187") (attacker_position "-1246 -478 237") (victim_position "-1221 -53 283")
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "kill assist" against "(.*)<(\d+)><(.*)><(Red|Blue)>" \x28assister_position "(.*)"\x29 \x28attacker_position "(.*)"\x29 \x28victim_position "(.*)"\x29', logdata)
        if (res):
            print "Player assisted in kill"
            pprint(res.groups())

            return

        #medic death ubercharge = 0 or 1, healing = amount healed in that life. kill message comes directly after
        #"%s<%i><%s><%s>" triggered "medic_death" against "%s<%i><%s><%s>" (healing "%d") (ubercharge "%s")
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "medic_death" against "(.*)<(\d+)><(.*)><(Red|Blue)>" \x28healing "(.*)"\x29 \x28ubercharge "(.*)"\x29)', logdata)
        if (res):
            print "Medic death"
            pprint(res.groups())

            return

        #ubercharge used
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "chargedeployed"', logdata)
        if (res):
            print "Ubercharge used"
            pprint(res.groups())
            
            return

        #point capture
        #/Team "(Blue|Red)" triggered "pointcaptured" \x28cp "(\d+)"\x29 \x28cpname "(.+)"\x29 \x28numcappers "(\d+)".+/
        #Team "Red" triggered "pointcaptured" (cp "0") (cpname "#koth_viaduct_cap") (numcappers "5") (player1 "[v3] Faithless<47><STEAM_0:0:52150090><Red>") (position1 "-1370 59 229") (player2 "[v3] Chrome<48><STEAM_0:1:41365809><Red>") (position2 "-1539 87 231") (player3 "[v3] Jak<49><STEAM_0:0:18518582><Red>") (position3 "-1659 150 224") (player4 "[v3] Kaki<51><STEAM_0:1:35387674><Red>") (position4 "-1685 146 224") (player5 "[v3] taintedromance<52><STEAM_0:0:41933053><Red>") (position5 "-1418 182 236")
        res = regex(r'Team "(Blue|Red)" triggered "pointcaptured" \x28cp "(\d+)"\x29 \x28cpname "(.*)"\x29 \x28numcappers "(\d+)"', logdata)
        if (res):
            print "Point captured"
            pprint(res.groups())

            return

        #capture block
        #"pvtx<103><STEAM_0:1:7540588><Red>" triggered "captureblocked" (cp "1") (cpname "Control Point B") (position "-2143 2284 156")
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "captureblocked" \x28cp "(\d+)"\x29 \x28cpname "#?(.*)"\x29 \x28position "(.*)"\x29', logdata)
        if (res):
            print "Capture blocked"
            pprint(res.groups())

            return

        #domination
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "domination" against "(.*)<(\d+)><(.*)><(Red|Blue)>"', logdata)
        if (res):
            print "Player dominated"
            pprint(res.groups())

            return

        #revenge
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "revenge" against "(.*)<(\d+)><(.*)><(Red|Blue)>"', logdata)
        if (res):
            print "Player got revenge"
            pprint(res.groups())

            return
        
        #suicide
        #"Hypnos<20><STEAM_0:0:24915059><Red>" committed suicide with "world" (customkill "train") (attacker_position "568 397 -511")
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" committed suicide with "(.*)" \x28customkill "(.*?)"\x29', logdata)
        if (res):
            print "Player committed suicide"
            pprint(res.groups())

            return

        #current score (shown after round win/round length
        res = regex(r'Team "(Blue|Red)" current score "(\d+)" with "(\d+)" players', logdata)
        if (res):
            print "Current scores"
            pprint(res.groups())

            return

        #engi building destruction
        #"dcup<109><STEAM_0:0:15236776><Red>" triggered "killedobject" (object "OBJ_SENTRYGUN") (weapon "tf_projectile_pipe") (objectowner "NsS. oLiVz<101><STEAM_0:1:15674014><Blue>") (attacker_position "551 2559 216")
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" triggered "killedobject" \x28object "(.*)"\x29 \x28weapon "(.*)"\x29 \x28objectowner "(.*)<(\d+)><(.*)><(Blue|Red)>)"\x29 \x28attacker_position "(.*)"\x29', logdata)
        if (res):
            print "Player destroyed engineer building"
            pprint(res.groups())

            return

        #final scores
        res = regex(r'Team "(Blue|Red)" final score "(\d+)" with "(\d+)" players', logdata)
        if (res):
            print "Final scores"
            pprint(res.groups())

            return

        #game over
        res = regex(r'World triggered "Game_Over" reason "(.*)"', logdata)
        if (res):
            print "Game over"
            pprint(res.groups())

            return

        #rcon command
        res = regex(r'rcon from "(.*?)": command "(.*)"', logdata)
        if (res):
            print "Someone issued rcon command"
            pprint(res.groups())

            return


        #disconnect RL 10/07/2012 - 01:13:44: "triple h<162><STEAM_0:1:33713004><Red>" disconnected (reason " #tf2pug")
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" disconnected \(reason "(.*)"\)', logdata)
        if (res):
            print "Player disconnected"
            pprint(res.groups())
            
            return
        
        #connect RL 10/07/2012 - 22:45:11: "GU | wm<3><STEAM_0:1:7175436><>" connected, address "124.168.51.7:27005"
        res = regex(r'"(.*)<(\d+)><(.*)><>" connected, address "(.*?):(.*)"', logdata)
        if (res):
            print "Player connected"
            pprint(res.groups())

            return
        #validated "hipsterhipster<4><STEAM_0:1:22674758><>" STEAM USERID validated
        res = regex(r'"(.*)<(\d+)><(.*)><>" STEAM USERID validated', logdata)
        if (res):
            print "Player validated"
            pprint(res.groups())

            return
        #chat
        res = regex(r'"(.+)<(\d+)><(.+)><(Red|Blue|Spectator)>" (say|say_team) "(.+)"', logdata)
        if (res):
            print "Chat was said"
            pprint(res.groups())

            return
        
        #class change    
        res = regex(r'"(.*)<(\d+)><(.*)><(Red|Blue)>" changed role to "(.*)"', logdata)
        if (res):
            print "Player changed class"
            pprint(res.groups())

            return

        #round win
        res = regex(r'World triggered "Round_Win".+winner.+"(Blue|Red)"', logdata)
        if (res):
            print "Round won"
            pprint(res.groups())

            return

        #overtime
        res = regex(r'World triggered "Round_Overtime"', logdata)
        if (res):
            print "Overtime"
            pprint(res.groups())

            return

        #round length
        res = regex(r'World triggered "Round_Length".+seconds.+"(\d+.\d+)', logdata)
        if (res):
            print "Round length"
            pprint(res.groups())
    
            return

        #round start
        res = regex(r'World triggered "Round_Start"', logdata)
        if (res):
            print "Round start"
            pprint(res.groups())

            return

        #setup end
        res = regex(r'World triggered "Round_Setup_End"', logdata)
        if (res):
            print "Round Setup End"
            pprint(res.groups())

            return

        #mini round win
        res = regex(r'World triggered "Mini_Round_Win" \x28winner "(Blue|Red)"\x29 \x28round "round_(\d+)"\x29', logdata)
        if (res):
            print "Mini round win"
            pprint(res.groups())

            return

        #mini round length
        res = regex(r'World triggered "Mini_Round_Length" \x28seconds "(\d+.\d+)"\x29', logdata)
        if (res):
            print "Mini round length"
            pprint(res.groups())

            return

    def regex(self, expression, string): #helper function for performing regular expression checks. avoids having to compile and match in-function 1000 times
        preg = re.compile(expression, re.IGNORECASE | re.MULTILINE)
        
        match = preg.search(string)
        #print expression + " match?: "
        #print match
        return match

    def regml(self, retuple, index): #get index of re group tuple
        return retuple.group(index)
