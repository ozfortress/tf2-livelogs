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
	
	EXECUTE 'CREATE TABLE ' || table_name || ' (steamid varchar(64) PRIMARY KEY, name text, team text, kills integer, deaths integer, assists integer, points decimal, healing_done integer,
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

CREATE OR REPLACE FUNCTION create_game_medic_table (unique_id text) RETURNS void AS $_$
DECLARE
	table_name varchar(128);
BEGIN
	table_name := 'log_medic_' || unique_id;

	EXECUTE 'CREATE TABLE ' || table_name || ' (eventid integer PRIMARY KEY, steamid varchar(64), uber_used integer, uber_lost integer)';
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION setup_log_tables (unique_id text) RETURNS void AS $_$
BEGIN
	PERFORM create_game_event_table(unique_id);
	PERFORM create_game_stat_table(unique_id);
	PERFORM create_game_kill_table(unique_id);
	PERFORM create_game_chat_table(unique_id);
	PERFORM create_game_round_table(unique_id);
	PERFORM create_game_medic_table(unique_id);
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION create_global_stat_table () RETURNS void AS $_$
BEGIN
	IF EXISTS (
		SELECT * 
		FROM pg_catalog.pg_tables
		WHERE tablename = 'livelogs_player_stats'
		)
	THEN
		RAISE NOTICE 'Table livelogs.livelogs_player_stats already exists';
	ELSE
		CREATE TABLE livelogs_player_stats (steamid varchar(64) PRIMARY KEY, name text, kills integer, deaths integer, assists integer, points decimal, healing_done integer,
					     healing_received integer, ubers_used integer, ubers_lost integer, damage_dealt integer, ap_small integer, ap_medium integer, ap_large integer,
					     mk_small integer, mk_medium integer, mk_large integer, captures integer, captures_blocked integer, dominations integer, revenges integer,
					     suicides integer, buildings_destroyed integer, wins integer, losses integer, draws integer);
	END IF;
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION pgsql_upsert (insert_query text, update_query text) RETURNS void AS $_$
--THIS FUNCTION WILL TAKE TWO QUERIES, AN INSERT AND AN UPDATE QUERY. IT WILL ATTEMPT TO RUN THE UPDATE QUERY FIRST, IF UNSUCCESSFUL IT WILL RUN THE INSERT QUERY
--Allows the user to avoid having to check the contents via their language first to decide whether to insert or update.
BEGIN
	LOOP
		--UPDATE
		EXECUTE update_query;
		--CHECK IF SUCCESSFUL
		IF found THEN
			RETURN;
		END IF;
		
		--UNSUCCESSFUL. RUN INSERT. This is where the loop comes in. If two updates are attempted at the same time it will cause a unique_violation. When this happens, we loop through again
		BEGIN
			EXECUTE insert_query;
			RETURN;
		EXCEPTION WHEN unique_violation THEN
			RETURN;
		END;
	END LOOP;
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION merge_stat_table (tablename text) RETURNS void AS $_$
--Merges all stats in a new log table with the master player stat table :o)
--SELECT merge_stat_table('log_stat_3232244481_61317_1349787463');
--COLUMNS: (steamid varchar(64) PRIMARY KEY, name text, kills integer, deaths integer, assists integer, points integer, healing_done integer,
--					     healing_received integer, ubers_used integer, ubers_lost integer, damage_dealt integer, ap_small integer, ap_medium integer, ap_large integer,
--					     mk_small integer, mk_medium integer, mk_large integer, captures integer, captures_blocked integer, dominations integer, revenges integer,
--					     suicides integer, buildings_destroyed integer)
BEGIN
	EXECUTE 'UPDATE livelogs_player_stats master SET
	
		name = newlog.name,
		kills = master.kills + newlog.kills,
		deaths = master.deaths + newlog.deaths,
		assists = master.assists + newlog.assists,
		points = master.points + newlog.points,
		healing_done = master.healing_done + newlog.healing_done,
		healing_received = master.healing_received + newlog.healing_received,
		ubers_used = master.ubers_used + newlog.ubers_used,
		damage_dealt = master.damage_dealt + newlog.damage_dealt,
		ap_small = master.ap_small + newlog.ap_small,
		ap_medium = master.ap_medium + newlog.ap_medium,
		ap_large = master.ap_large + newlog.ap_large,
		mk_small = master.mk_small + newlog.mk_small,
		mk_medium = master.mk_medium + newlog.mk_medium,
		mk_large = master.mk_large + newlog.mk_large,
		captures = master.captures + newlog.captures,
		captures_blocked = master.captures_blocked + newlog.captures_blocked,
		dominations = master.dominations + newlog.dominations,
		revenges = master.revenges + newlog.revenges,
		suicides = master.suicides + newlog.suicides,
		buildings_destroyed = master.buildings_destroyed + newlog.buildings_destroyed
		
	FROM ' || tablename || ' newlog
	WHERE master.steamid = newlog.steamid';

	EXECUTE 'INSERT INTO livelogs_player_stats (SELECT * FROM ' || tablename || ' WHERE ' || tablename || '.steamid 
						NOT IN (SELECT steamid FROM livelogs_player_stats))';
END;
$_$ LANGUAGE 'plpgsql';