
CREATE OR REPLACE FUNCTION create_game_event_table (unique_id text) RETURNS void AS $_$
DECLARE
	table_name varchar(128);
BEGIN
	table_name := 'log_event_' || unique_id;
	
	EXECUTE 'CREATE TABLE ' || table_name || ' (eventid serial PRIMARY KEY, event_time text, event_type text,
						    kill_attacker_id varchar(64), kill_attacker_pos varchar(32),
						    kill_assister_id varchar(64), kill_assister_pos varchar(32),
						    kill_victim_id varchar(64), kill_victim_pos varchar(32),
						    medic_steamid varchar(64), medic_uber_used integer, medic_uber_lost integer, medic_healing integer,
						    capture_name varchar(64), capture_team varchar(16), capture_num_cappers integer, capture_blocked integer,
						    round_winner varchar(16), round_red_score integer, round_blue_score integer, round_length decimal,
						    game_over_reason varchar(128))';
END;
$_$ LANGUAGE 'plpgsql';


CREATE OR REPLACE FUNCTION create_game_stat_table (unique_id text) RETURNS void AS $_$
DECLARE
	table_name varchar(128);
BEGIN
	table_name := 'log_stat_' || unique_id;
	
	EXECUTE 'CREATE TABLE ' || table_name || ' (steamid varchar(64) PRIMARY KEY, name text, kills integer, deaths integer, assists integer, points decimal, 
					     healing_done integer, healing_received integer, ubers_used integer, ubers_lost integer, 
					     headshots integer, backstabs integer, damage_dealt integer, damage_taken integer,
					     ap_small integer, ap_medium integer, ap_large integer,
					     mk_small integer, mk_medium integer, mk_large integer, 
					     captures integer, captures_blocked integer, 
					     dominations integer, times_dominated integer, revenges integer,
					     suicides integer, buildings_destroyed integer, extinguishes integer, kill_streak integer)';

	EXECUTE 'CREATE TRIGGER zero_null_stat
		 BEFORE INSERT ON ' || table_name || '
			FOR EACH ROW EXECUTE PROCEDURE zero_null_stat()';

END;
$_$ LANGUAGE 'plpgsql';


CREATE OR REPLACE FUNCTION create_game_chat_table (unique_id text) RETURNS void AS $_$
DECLARE
	table_name varchar(128);
BEGIN
	table_name := 'log_chat_' || unique_id;
	
	EXECUTE 'CREATE TABLE ' || table_name || ' (eventid integer PRIMARY KEY, steamid varchar(64), name text, team text, chat_type varchar(12), chat_message text)';
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION create_game_team_table (unique_id text) RETURNS void AS $_$
DECLARE
	table_name varchar(128);
BEGIN
	table_name := 'log_team_' || unique_id;
	
	EXECUTE 'CREATE TABLE ' || table_name || ' (steamid varchar(64) PRIMARY KEY, team text)';
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION setup_log_tables (unique_id text) RETURNS void AS $_$
BEGIN
	PERFORM create_game_event_table(unique_id);
	PERFORM create_game_stat_table(unique_id);
	PERFORM create_game_chat_table(unique_id);
	PERFORM create_game_team_table(unique_id);
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
		CREATE TABLE livelogs_player_stats (steamid varchar(64) PRIMARY KEY, name text, kills integer, deaths integer, assists integer, points decimal, 
		                             healing_done integer, healing_received integer, ubers_used integer, ubers_lost integer, 
		                             headshots integer, backstabs integer, damage_dealt integer, damage_taken integer,
		                             ap_small integer, ap_medium integer, ap_large integer,
					     mk_small integer, mk_medium integer, mk_large integer,
					     captures integer, captures_blocked integer, 
					     dominations integer, times_dominated integer, revenges integer,
					     suicides integer, buildings_destroyed integer, extinguishes integer, kill_streak integer,
					     wins integer, losses integer, draws integer);

		
	END IF;

	DROP TRIGGER IF EXISTS zero_null_stat ON livelogs_player_stats;

	CREATE TRIGGER zero_null_stat
	BEFORE INSERT ON livelogs_player_stats
		FOR EACH ROW EXECUTE PROCEDURE zero_null_stat();
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION create_global_server_table () RETURNS void AS $_$
BEGIN
	IF EXISTS (
		SELECT *
		FROM pg_catalog.pg_tables
		WHERE tablename = 'livelogs_servers'
		)
	THEN
		RAISE NOTICE 'Table livelogs.livelogs_servers already exists';
	ELSE
		CREATE TABLE livelogs_servers (numeric_id serial, server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64), map varchar(64) NOT NULL, log_name text, live boolean, webtv_port integer, PRIMARY KEY (numeric_id, log_ident));
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
--COLUMNS: steamid varchar(64) PRIMARY KEY, name text, team text, kills integer, deaths integer, assists integer, points decimal, 
--					     healing_done integer, healing_received integer, ubers_used integer, ubers_lost integer, 
--					     headshots integer, backstabs integer, damage_taken integer, damage_dealt integer, 
--					     ap_small integer, ap_medium integer, ap_large integer,
--					     mk_small integer, mk_medium integer, mk_large integer, 
--					     captures integer, captures_blocked integer, 
--					     dominations integer, times_dominated integer, revenges integer,
--					     suicides integer, buildings_destroyed integer, extinguishes integer, kill_streak integer)';
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
		ubers_lost = master.ubers_lost + newlog.ubers_lost,
		headshots = master.headshots + newlog.headshots,
		backstabs = master.backstabs + newlog.backstabs,
		damage_dealt = master.damage_dealt + newlog.damage_dealt,
		damage_taken = master.damage_taken + newlog.damage_taken,
		ap_small = master.ap_small + newlog.ap_small,
		ap_medium = master.ap_medium + newlog.ap_medium,
		ap_large = master.ap_large + newlog.ap_large,
		mk_small = master.mk_small + newlog.mk_small,
		mk_medium = master.mk_medium + newlog.mk_medium,
		mk_large = master.mk_large + newlog.mk_large,
		captures = master.captures + newlog.captures,
		captures_blocked = master.captures_blocked + newlog.captures_blocked,
		dominations = master.dominations + newlog.dominations,
		times_dominated = master.times_dominated + newlog.times_dominated,
		revenges = master.revenges + newlog.revenges,
		suicides = master.suicides + newlog.suicides,
		buildings_destroyed = master.buildings_destroyed + newlog.buildings_destroyed,
		extinguishes = master.extinguishes + newlog.extinguishes,
		kill_streak = newlog.kill_streak
		
	FROM ' || tablename || ' newlog
	WHERE master.steamid = newlog.steamid';

	EXECUTE 'INSERT INTO livelogs_player_stats (
						SELECT *
						FROM ' || tablename || ' WHERE ' || tablename || '.steamid 
							NOT IN (SELECT steamid FROM livelogs_player_stats))';

							--steamid, name, kills, deaths, assists, points, 
							--healing_done, healing_received, ubers_used, ubers_lost,
							--headshots, backstabs, damage_dealt, 
							--ap_small, ap_medium, ap_large, 
							--mk_small, mk_medium, mk_large, 
							--captures, captures_blocked, 
							--dominations, times_dominated, revenges, 
							--suicides, buildings_destroyed, extinguishes, kill_streak
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION add_stat_column (col_name text, col_type regtype) RETURNS void AS $_$
DECLARE
	row RECORD;
BEGIN
	FOR row IN
		SELECT table_name
		FROM information_schema.tables 
		WHERE table_catalog = 'livelogs' AND table_name ~* 'log_stat'
	LOOP
		IF EXISTS (
			SELECT column_name
			FROM information_schema.columns 
			WHERE table_name = row.table_name AND column_name = col_name
			)
		THEN
			RAISE NOTICE 'Column % already exists', col_name;
		ELSE
			EXECUTE 'ALTER TABLE ' || row.table_name || ' ADD COLUMN ' || col_name || ' ' || col_type;
		END IF;
	END LOOP;

	IF NOT EXISTS (
		SELECT column_name
		FROM information_schema.columns
		WHERE table_name = 'livelogs_player_stats' AND column_name = col_name
		)
	THEN
		EXECUTE 'ALTER TABLE livelogs_player_stats ADD COLUMN ' || col_name || ' ' || col_type;
	END IF;
END;
$_$ LANGUAGE 'plpgsql';