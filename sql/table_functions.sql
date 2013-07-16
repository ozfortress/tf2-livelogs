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

CREATE OR REPLACE FUNCTION setup_log_tables (unique_id text) RETURNS void AS $_$
BEGIN
    PERFORM create_game_event_table(unique_id);
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
            --RETURN;
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
--                         healing_done integer, healing_received integer, ubers_used integer, ubers_lost integer, 
--                         headshots integer, backstabs integer, damage_taken integer, damage_dealt integer, 
--                         ap_small integer, ap_medium integer, ap_large integer,
--                         mk_small integer, mk_medium integer, mk_large integer, 
--                         captures integer, captures_blocked integer, 
--                         dominations integer, times_dominated integer, revenges integer,
--                         suicides integer, buildings_destroyed integer, extinguishes integer, kill_streak integer)';
DECLARE
    statrow RECORD;

BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables WHERE table_catalog = 'livelogs' AND table_name = tablename
        )
    THEN
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

        FOR statrow IN
            EXECUTE 'SELECT steamid, name, kills, deaths, assists, points, 
                                    healing_done, healing_received, ubers_used, ubers_lost, 
                                    headshots, backstabs, damage_dealt, damage_taken, 
                                    ap_small, ap_medium, ap_large, mk_small, mk_medium, mk_large,
                                    captures, captures_blocked, dominations, times_dominated, revenges, suicides,
                                    buildings_destroyed, extinguishes, kill_streak
                                    FROM ' || tablename || ' WHERE ' || tablename || '.steamid
                                    NOT IN (SELECT steamid FROM livelogs_player_stats)'
        LOOP
            INSERT INTO livelogs_player_stats (steamid, name, kills, deaths, assists, points, 
                                                healing_done, healing_received, ubers_used, ubers_lost, 
                                                headshots, backstabs, damage_dealt, damage_taken, 
                                                ap_small, ap_medium, ap_large, mk_small, mk_medium, mk_large,
                                                captures, captures_blocked, dominations, times_dominated, revenges, suicides,
                                                buildings_destroyed, extinguishes, kill_streak)
                                            VALUES (statrow.steamid, statrow.name, statrow.kills, statrow.deaths, statrow.assists, statrow.points,
                                                statrow.healing_done, statrow.healing_received, statrow.ubers_used, statrow.ubers_lost,
                                                statrow.headshots, statrow.backstabs, statrow.damage_dealt, statrow.damage_taken,
                                                statrow.ap_small, statrow.ap_medium, statrow.ap_large, statrow.mk_small, statrow.mk_medium, statrow.mk_large,
                                                statrow.captures, statrow.captures_blocked, statrow.dominations, statrow.times_dominated, statrow.revenges, statrow.suicides,
                                                statrow.buildings_destroyed, statrow.extinguishes, statrow.kill_streak);

        END LOOP;
    ELSE
        RAISE NOTICE 'Table that was asked to be merged does not exist';
    END IF;
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION add_stat_column (col_name text, col_type regtype) RETURNS void AS $_$
BEGIN
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

DROP TYPE IF EXISTS class_stat_record CASCADE; --cascade so it'll drop items using this type too
CREATE TYPE class_stat_record AS (
    --class, kills, deaths, assists, points
    --healing_done, healing_received, ubers_used, ubers_lost,
    --headshots, backstabs, damage_dealt, damage_taken,
    --dominations, revenges
    class text,
    kills bigint,
    deaths bigint,
    assists bigint,
    points decimal,
    healing_done bigint,
    healing_received bigint,
    ubers_used bigint,
    ubers_lost bigint,
    headshots bigint,
    backstabs bigint,
    damage_dealt bigint,
    damage_taken bigint,
    dominations bigint,
    revenges bigint
);

CREATE OR REPLACE FUNCTION get_player_class_stats(cid bigint) RETURNS setof class_stat_record AS $_$
DECLARE
    pclass RECORD;
    class_stats class_stat_record;
BEGIN
    FOR pclass IN
        SELECT DISTINCT class
        FROM livelogs_player_stats
        WHERE steamid = cid
    LOOP
        SELECT 1, SUM(kills) as kills, SUM(deaths) as deaths, SUM(assists) as assists, SUM(points) as points, 
               SUM(healing_done) as healing_done, SUM(healing_received) as healing_received, SUM(ubers_used) as ubers_used, SUM(ubers_lost) as ubers_lost, 
               SUM(headshots) as headshots, SUM(backstabs) as backstabs, SUM(damage_dealt) as damage_dealt, SUM(damage_taken) as damage_taken,
               SUM(dominations) as dominations, SUM(revenges) as revenges
        FROM livelogs_player_stats
        WHERE steamid = cid AND class = pclass.class
        INTO class_stats;

        class_stats.class := pclass.class;

        RETURN NEXT class_stats; 
    END LOOP;
END;
$_$ LANGUAGE 'plpgsql';

DROP TYPE IF EXISTS user_log_return CASCADE; --we add cascade so that it will drop items using this type as well
CREATE TYPE user_log_return AS (
    server_ip varchar(32),
    server_port integer,
    log_ident varchar(64),
    map varchar(64),
    log_name text,
    live boolean
);

CREATE OR REPLACE FUNCTION get_user_logs(sid text) RETURNS setof user_log_return AS $_$
DECLARE
    row RECORD;
    select_result boolean;
    return_count integer;
BEGIN
    return_count := 0;
    FOR row IN
        --SELECT table_name FROM information_schema.tables
        --WHERE table_catalog = 'livelogs' AND table_name ~* 'log_stat'

        SELECT server_ip, server_port, log_ident, map, log_name, live FROM livelogs_servers
    LOOP
        EXECUTE 'SELECT EXISTS (SELECT steamid FROM log_stat_' || row.log_ident || ' WHERE steamid = ''' || sid || ''')' INTO select_result;
        
        IF select_result THEN
            RETURN NEXT row;
            return_count := return_count + 1;
        ELSE
            CONTINUE;
        END IF;
    END LOOP;
    RETURN;

END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION get_user_logs(sid text, query_limit integer) RETURNS setof user_log_return AS $_$
DECLARE
    row RECORD;
    select_result boolean;
    return_count integer;
BEGIN
    return_count := 0;
    FOR row IN
        --SELECT table_name FROM information_schema.tables
        --WHERE table_catalog = 'livelogs' AND table_name ~* 'log_stat'

        SELECT server_ip, server_port, log_ident, map, log_name, live FROM livelogs_servers ORDER BY numeric_id DESC
    LOOP
        IF return_count = query_limit THEN
            RETURN;
        END IF;

        EXECUTE 'SELECT EXISTS (SELECT steamid FROM log_stat_' || row.log_ident || ' WHERE steamid = ''' || sid || ''')' INTO select_result;
        
        IF select_result THEN
            RETURN NEXT row;
            return_count := return_count + 1;
        ELSE
            CONTINUE;
        END IF;
    END LOOP;
    RETURN;

END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION index_user_logs() RETURNS void AS $_$
DECLARE
    row RECORD;
    logrow RECORD;
BEGIN
    RAISE NOTICE 'Warning: This will take a while on a large database!';

    FOR row IN
        SELECT DISTINCT log_ident, steamid FROM livelogs_player_stats
    LOOP
        SELECT name
        FROM livelogs_player_stats JOIN livelogs_servers ON livelogs_player_stats.log_ident = livelogs_servers.log_ident 
        WHERE steamid = row.steamid and name IS NOT NULL
        ORDER BY numeric_id DESC LIMIT 1 INTO logrow;

        INSERT INTO livelogs_player_details (steamid, log_ident, name) VALUES (row.steamid, row.log_ident, logrow.name);
    END LOOP;
    RETURN;
END;
$_$ LANGUAGE 'plpgsql';
