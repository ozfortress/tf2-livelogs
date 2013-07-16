
CREATE TABLE livelogs_auth_keys (user_name text, user_email text, user_key text, user_ip text); --holds user authentication keys and contact details

CREATE TABLE livelogs_player_stats (index serial, log_ident varchar(64), steamid bigint, team text, class text,
                                    kills integer, deaths integer, assists integer, points decimal, 
                                    healing_done integer, healing_received integer, ubers_used integer, ubers_lost integer, 
                                    headshots integer, backstabs integer, damage_dealt integer, damage_taken integer,
                                    ap_small integer, ap_medium integer, ap_large integer,
                                    mk_small integer, mk_medium integer, mk_large integer,
                                    captures integer, captures_blocked integer, 
                                    dominations integer, times_dominated integer, revenges integer,
                                    suicides integer, buildings_destroyed integer, extinguishes integer, PRIMARY KEY(log_ident, steamid, class)); --holds per-game player statistics. i.e, the stat table for all matches


CREATE TRIGGER zero_null_stat
        BEFORE INSERT ON livelogs_player_stats
        FOR EACH ROW EXECUTE PROCEDURE zero_null_stat();


CREATE TABLE livelogs_game_chat (id serial, log_ident varchar(64), steamid bigint, name text, team text, chat_type varchar(12), chat_message text); --global chat table

CREATE TABLE livelogs_log_index (numeric_id serial, server_ip cidr NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean, webtv_port integer, tstamp text); --holds server log information

CREATE TABLE livelogs_player_details (id serial, steamid bigint, log_ident varchar(64), name text);
