CREATE OR REPLACE FUNCTION create_game_event_table (unique_id text) RETURNS void AS $_$
DECLARE
	table_name varchar(128);
BEGIN
	table_name := 'log_event_' || unique_id;
	
	EXECUTE 'CREATE TABLE ' || table_name || ' (eventid serial PRIMARY KEY, time text, event_type text)';
END;
$_$ LANGUAGE 'plpgsql';


CREATE OR REPLACE FUNCTION create_game_stat_table (unique_id text) RETURNS void AS $_$
DECLARE
	table_name varchar(128);
BEGIN
	table_name := 'log_stat_' || unique_id;
	
	EXECUTE 'CREATE TABLE ' || table_name || ' (steamid varchar(64) PRIMARY KEY, name text, kills integer, deaths integer, assists integer, points integer, healing_done integer,
					     healing_received integer, ubers_used integer, ubers_lost integer, damage_dealt integer, ap_small integer, ap_medium integer, ap_large integer,
					     mk_small integer, mk_medium integer, mk_large integer, captures integer, captures_blocked integer, dominations integer, revenges integer,
					     suicides integer, buildings_destroyed integer)';
END;
$_$ LANGUAGE 'plpgsql';


CREATE OR REPLACE FUNCTION create_game_kill_table (unique_id text) RETURNS void AS $_$
DECLARE
	table_name varchar(128);
BEGIN
	table_name := 'log_kill_' || unique_id;
	
	EXECUTE 'CREATE TABLE ' || table_name || ' (eventid integer PRIMARY KEY, attacker_id varchar(64), attacker_pos varchar(32),
	                                                                         assister_id varchar(64), assister_pos varchar(32),
	                                                                         victim_id varchar(64), victim_pos varchar(32))';
END;
$_$ LANGUAGE 'plpgsql';


CREATE OR REPLACE FUNCTION create_game_chat_table (unique_id text) RETURNS void AS $_$
DECLARE
	table_name varchar(128);
BEGIN
	table_name := 'log_chat_' || unique_id;
	
	EXECUTE 'CREATE TABLE ' || table_name || ' (eventid integer PRIMARY KEY, steamid varchar(64), chat_type varchar(12), chat_message text)';
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION create_game_round_table (unique_id text) RETURNS void AS $_$
DECLARE
	table_name varchar(128);
BEGIN
	table_name := 'log_round_' || unique_id;
	
	EXECUTE 'CREATE TABLE ' || table_name || ' (eventid integer PRIMARY KEY, red_score integer, blue_score integer, round_length decimal)';
END;
$_$ LANGUAGE 'plpgsql';


CREATE OR REPLACE FUNCTION setup_log_tables (unique_id text) RETURNS void AS $_$
BEGIN
	PERFORM create_game_event_table(unique_id);
	PERFORM create_game_stat_table(unique_id);
	PERFORM create_game_kill_table(unique_id);
	PERFORM create_game_chat_table(unique_id);
	PERFORM create_game_round_table(unique_id);
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION create_global_stat_table () RETURNS void AS $_$
BEGIN
	IF EXISTS (
		SELECT *
		FROM pg_catalog.pg_tables
		WHERE schemaname = 'livelogs'
		AND tablename = 'livelogs_player_stats'
		)
	THEN
		RAISE NOTICE 'Table livelogs.livelogs_player_stats already exists';
	ELSE
		CREATE TABLE livelogs.livelogs_player_stats ();
	END IF;
END;
$_$ LANGUAGE 'plpgsql';