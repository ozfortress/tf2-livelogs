"""
Simple program to add new users to the livelogs database


"""

try:
    import psycopg2
except ImportError:
    print """You are missing psycopg2.
    Install using `pip install psycopg2` or visit http://initd.org/psycopg/
    """
    quit()

import argparse
import string
import random

def random_string(len=24, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    #generates a random string of length len
    return ''.join(random.choice(chars) for x in range(len))



if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--name', help="User's name")
    parser.add_argument('--email', help="User's email")
    parser.add_argument('--ip', help="User's server IP")
    parser.add_argument('--key', help="User's API key (optional)")

    args = parser.parse_args()

    if not (args.name and args.email and args.ip):
        print "Invalid usage"
        quit()

    else:
        if args.key:
            client_key = args.key
        else:
            client_key = random_string(23)
            client_key = random.choice(string.digits) + client_key #append a random number to the start of the key, so sv_logsecret works

        try:
            db = psycopg2.connect("dbname=livelogs user=livelogs host=127.0.0.1 password=hello")
        except:
            print "Unable to connect to livelogs database"
            quit()

        try:
            cursor = db.cursor()

            cursor.execute("INSERT INTO livelogs_auth_keys (user_name, user_email, user_key, user_ip) VALUES (%s, %s, %s, %s)",
                                                            (args.name, args.email, client_key, args.ip,))

            cursor.close()

            db.commit()

            print "User added to the database. Server cvars:"

        except Exception, e:
            print "Error inserting data into database: %s" % e
            db.rollback()

        db.close()

        print "livelogs_address \"medic.ozfortress.com\""
        print "livelogs_port \"61222\""
        print "livelogs_api_key \"%s\"" % client_key


