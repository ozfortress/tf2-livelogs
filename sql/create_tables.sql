
-- AUTH TABLE
CREATE TABLE livelogs_auth_keys (user_name text, user_email text, user_key text, user_ip text); --holds user authentication keys and contact details

--holds per-game player statistics. i.e. the stat table for all matches
CREATE TABLE livelogs_player_stats (num_id serial, log_ident varchar(64), steamid bigint, team text, class text,
                                    kills integer, deaths integer, assists integer, points decimal, 
                                    healing_done integer, healing_received integer, ubers_used integer, ubers_lost integer,
                                    overhealing_done integer, overhealing_received integer,
                                    headshots integer, backstabs integer, damage_dealt integer, damage_taken integer,
                                    ap_small integer, ap_medium integer, ap_large integer,
                                    mk_small integer, mk_medium integer, mk_large integer,
                                    captures integer, captures_blocked integer, 
                                    dominations integer, times_dominated integer, revenges integer,
                                    suicides integer, buildings_destroyed integer, extinguishes integer, PRIMARY KEY(log_ident, steamid, class));

CREATE INDEX stat_ident_index ON livelogs_player_stats(log_ident);
CREATE INDEX stat_cid_index ON livelogs_player_stats(steamid);

-- TRIGGER FOR STAT TABLE - replaces NULL entires with 0
CREATE TRIGGER zero_null_stat
        BEFORE INSERT ON livelogs_player_stats
        FOR EACH ROW EXECUTE PROCEDURE zero_null_stat();

-- CHAT TABLE
CREATE TABLE livelogs_game_chat (id serial, log_ident varchar(64), steamid bigint, name text, team text, chat_type varchar(12), chat_message text); --global chat table
CREATE INDEX chat_ident_index ON livelogs_game_chat(log_ident);

-- LOG INDEX
CREATE TABLE livelogs_log_index (numeric_id serial, server_ip cidr NOT NULL, server_port integer NOT NULL, api_key text references livelogs_auth_keys(user_key), log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean, webtv_port integer, tstamp text); --holds server log information
CREATE INDEX log_ident_index ON livelogs_log_index(log_ident);

-- PLAYER DETAILS CONTAINS STEAMIDS AND THE LOGS THEY ARE IN
CREATE TABLE livelogs_player_details (id serial, steamid bigint, log_ident varchar(64), name text);
CREATE INDEX details_ident_index ON livelogs_player_details(log_ident);

------ EVENTS TABLES
CREATE TABLE livelogs_game_events (eventid serial PRIMARY KEY, log_ident varchar(64), event_time text, event_type text,
                            capture_name varchar(64), capture_team varchar(16), capture_num_cappers integer, capture_blocked integer,
                            round_winner varchar(16), round_red_score integer, round_blue_score integer, round_length decimal,
                            game_over_reason varchar(128));

CREATE INDEX game_events_ident_index ON livelogs_game_events(log_ident);
CREATE INDEX game_events_eventid_ident_index ON livelogs_game_events(eventid, log_ident);

CREATE TABLE livelogs_kill_events (eventid serial PRIMARY KEY, log_ident text, event_time text, event_type text,
                                kill_attacker_id bigint, kill_attacker_pos varchar(32),
                                kill_assister_id bigint, kill_assister_pos varchar(32),
                                kill_victim_id bigint, kill_victim_pos varchar(32));

CREATE INDEX kill_events_ident_index ON livelogs_kill_events(log_ident);
CREATE INDEX kill_events_eventid_ident_index ON livelogs_kill_events(eventid, log_ident);

CREATE TABLE livelogs_medic_events (eventid serial PRIMARY KEY, log_ident text, event_time text, event_type text,
                                    medic_steamid bigint, medic_uber_used integer, medic_uber_lost integer, medic_healing integer);

CREATE INDEX medic_events_ident_index ON livelogs_medic_events(log_ident);
CREATE INDEX medic_events_eventid_ident_index ON livelogs_medic_events(eventid, log_ident);
