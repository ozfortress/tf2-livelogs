
CREATE TABLE livelogs_auth_keys (user_name text, user_email text, user_key text, user_ip text); --holds user authentication keys and contact details

CREATE TABLE livelogs_player_stats (steamid varchar(64) PRIMARY KEY, name text, kills integer, deaths integer, assists integer, points decimal, 
                                     healing_done integer, healing_received integer, ubers_used integer, ubers_lost integer, 
                                     headshots integer, backstabs integer, damage_dealt integer, damage_taken integer,
                                     ap_small integer, ap_medium integer, ap_large integer,
                                     mk_small integer, mk_medium integer, mk_large integer,
                                     captures integer, captures_blocked integer, 
                                     dominations integer, times_dominated integer, revenges integer,
                                     suicides integer, buildings_destroyed integer, extinguishes integer, kill_streak integer,
                                     wins integer, losses integer, draws integer); --holds all player statistics

CREATE TABLE livelogs_servers (numeric_id serial, server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean, webtv_port integer); --holds server log information

CREATE TABLE livelogs_player_logs (index serial PRIMARY KEY, 
                                   steamid varchar(64), 
                                   log_ident varchar(64) references livelogs_servers(log_ident)); --holds steamids and log idents for player indexing