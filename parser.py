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


    def parse(self, logString):
        print "PARSING LOG: %s" % logString

        res = self.regex("(.*)", logString)
        if (res):
            print "Matching regex:"
            pprint(res.groups())

    def regex(self, expression, string):
        preg = re.compile(expression, re.IGNORECASE)

        match = preg.match(string)
        return match