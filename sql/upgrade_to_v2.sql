CREATE OR REPLACE FUNCTION restore_index() RETURNS void AS $_$
DECLARE
    index_row RECORD;
    tstamp_data TEXT;
BEGIN
    SELECT CAST(to_char(now(), 'YYYY-MM-DD HH24:MI:SS') as TEXT) INTO tstamp_data;

    FOR index_row IN
        SELECT * FROM old_index ORDER BY numeric_id DESC
    LOOP
        INSERT INTO livelogs_log_index (server_ip, server_port, log_ident, map, log_name, live, webtv_port, tstamp)
        VALUES (CAST(index_row.server_ip AS CIDR), index_row.server_port, index_row.log_ident, index_row.map, index_row.log_name, 'false', 0, tstamp_data);
    END LOOP;
END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION restore_stats_and_names() RETURNS void AS $_$
DECLARE
    index_row RECORD;
    log_row RECORD;
    fake_id integer := 1;
BEGIN
    RAISE NOTICE 'Updating stat table with previous stats. This will take a LONG while';

    FOR index_row IN
        SELECT log_ident FROM livelogs_log_index
    LOOP
        FOR log_row IN
            EXECUTE 'SELECT name, team,
                    kills, deaths, assists, points,
                    healing_done, healing_received, ubers_used, ubers_lost,
                    headshots, backstabs, damage_dealt, damage_taken,
                    captures, captures_blocked,
                    dominations, times_dominated, revenges,
                    suicides, buildings_destroyed, extinguishes
                    FROM log_stat_' || index_row.log_ident
        LOOP
            INSERT INTO livelogs_player_stats (log_ident, steamid, team, class, kills, deaths, assists, points, healing_done, healing_received, ubers_used, ubers_lost,
                                                headshots, backstabs, damage_dealt, damage_taken, captures, captures_blocked, dominations, times_dominated, revenges,
                                                suicides, buildings_destroyed, extinguishes)
                VALUES (index_row.log_ident, fake_id, log_row.team, 'UNKNOWN', log_row.kills, log_row.deaths, log_row.assists, log_row.points, log_row.healing_done, log_row.healing_received, log_row.ubers_used,
                        log_row.ubers_lost, log_row.headshots, log_row.backstabs, log_row.damage_dealt, log_row.damage_taken, log_row.captures, log_row.captures_blocked, log_row.domnations, log_row.times_dominated,
                        log_row.revenges, log_row.suicides, log_row.buildings_destroyed, log_row.extinguishes);

            INSERT INTO livelogs_player_details (steamid, log_ident, name) VALUES (fake_id, index_row.log_ident, log_row.name);

            fake_id := fake_id + 1;
        END LOOP;
    END LOOP;

END;
$_$ LANGUAGE 'plpgsql';

CREATE OR REPLACE FUNCTION restore_chat() RETURNS void AS $_$
DECLARE
    index_row RECORD;
    chat_row RECORD;
    fake_id integer := 1;
BEGIN
    RAISE NOTICE 'Updating chat table with previous chat. This will take a LONG while';

    FOR index_row IN
        SELECT log_ident FROM livelogs_log_index
    LOOP
        FOR chat_row IN
            EXECUTE 'SELECT steamid, name, team,
                    chat_type, chat_message
                    FROM log_chat_' || index_row.log_ident
        LOOP
            INSERT INTO livelogs_game_chat (log_ident, steamid, name, team, chat_type, chat_message)
                VALUES (index_row.log_ident, fake_id, chat_row.name, chat_row.team, chat_row.chat_type, chat_row.chat_message);

            fake_id := fake_id + 1;
        END LOOP;
    END LOOP;
END;
$_$ LANGUAGE 'plpgsql';
