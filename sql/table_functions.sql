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
