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

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--name', help="User's name")
    parser.add_argument('--email', help="User's email")
    parser.add_argument('--ip', help="User's server IP")
    parser.add_argument('--key', help="User's API key")

    args = parser.parse_args()

    if not (args.name and args.email and args.ip and args.key):
        print "Invalid usage"
        quit()

    else:
        try:
            db = psycopg2.connect("dbname=livelogs user=livelogs host=127.0.0.1 password=hello")
        except:
            print "Unable to connect to livelogs database"
            quit()

        else:
            try:
                cursor = db.cursor()

                cursor.execute("INSERT INTO livelogs_auth_keys (user_name, user_email, user_key, user_ip) VALUES (%s, %s, %s, %s)",
                                                                (args.name, args.email, args.key, args.ip,))

                cursor.close()

                db.commit()

            except Exception, e:
                print "Error inserting data into database: %s" % e
                db.rollback()

            db.close()

