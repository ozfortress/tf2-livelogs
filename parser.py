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

        query = "CREATE TABLE log_%s (id serial PRIMARY KEY, num int, text varchar)" % self.UNIQUE_IDENT
        self.dbCursor.execute(query)

        query = "INSERT INTO log_%s (num, text) VALUES (%%s, %%s)" % self.UNIQUE_IDENT
        self.dbCursor.execute(query, (10, "hi friend",))

        query = "SELECT * FROM log_%s" % self.UNIQUE_IDENT
        self.dbCursor.execute(query)

        self.dbCursor.fetchone()

        self.psqlConn.commit()

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

        #res = regex("(.*)", logdata)

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

        #rcon command
        res = regex('rcon from "(.*?)": command "(.*)"', logdata)
        if (res):
            print "Someone issued rcon command"
            pprint(res.groups())

            return
        #disconnect RL 10/07/2012 - 01:13:44: "triple h<162><STEAM_0:1:33713004><Red>" disconnected (reason " #tf2pug")
        res = regex('"(.*)<(\d+)><(.*)><(Red|Blue)>" disconnected \(reason "(.*)"\)', logdata)
        if (res):
            print "Player disconnected"
            pprint(res.groups())

            return

        #connect RL 10/07/2012 - 22:45:11: "GU | wm<3><STEAM_0:1:7175436><>" connected, address "124.168.51.7:27005"
        res = regex('"(.*)<(\d+)><(.*)><>" connected, address "(.*?):(.*)"', logdata)
        if (res):
            print "Player connected"
            pprint(res.groups())

            return
        #validated "hipsterhipster<4><STEAM_0:1:22674758><>" STEAM USERID validated


    def regex(self, expression, string): #helper function for performing regular expression checks. avoids having to compile and match in-function 1000 times
        preg = re.compile(expression, re.IGNORECASE | re.MULTILINE)

        match = preg.search(string)

        print match
        return match