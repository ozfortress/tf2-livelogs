CREATE OR REPLACE FUNCTION zero_null_stat () RETURNS trigger AS $_$
BEGIN
        -- Function will replace NULL inserts with a 0, to make UPDATING using the merge function possible
        --
        --
        --
        --                          log_ident varchar(64), steamid bigint, team text, class text,
        --                          kills integer, deaths integer, assists integer, points decimal, 
        --                          healing_done integer, healing_received integer, ubers_used integer, ubers_lost integer,
        --                          overhealing_done integer, overhealing_received integer,
        --                          headshots integer, airshots integer, backstabs integer, 
        --                          damage_dealt integer, damage_taken integer,
        --                          ap_small integer, ap_medium integer, ap_large integer,
        --                          mk_small integer, mk_medium integer, mk_large integer,
        --                          captures integer, captures_blocked integer, 
        --                          dominations integer, times_dominated integer, revenges integer,
        --                          suicides integer, buildings_destroyed integer, extinguishes integer

        IF NEW.kills IS NULL THEN
                NEW.kills := 0;
        END IF;
        IF NEW.deaths IS NULL THEN
                NEW.deaths := 0;
        END IF;
        IF NEW.assists IS NULL THEN
                NEW.assists := 0;
        END IF;
        IF NEW.points IS NULL THEN
                NEW.points := 0;
        END IF;
        IF NEW.healing_done IS NULL THEN
                NEW.healing_done := 0;
        END IF;
        IF NEW.healing_received IS NULL THEN
                NEW.healing_received := 0;
        END IF;
        IF NEW.overhealing_done is NULL THEN
                NEW.overhealing_done := 0;
        END IF;
        IF NEW.overhealing_received IS NULL THEN
                NEW.overhealing_received := 0;
        END IF;
        IF NEW.ubers_used IS NULL THEN
                NEW.ubers_used := 0;
        END IF;
        IF NEW.ubers_lost IS NULL THEN
                NEW.ubers_lost := 0;
        END IF;
        IF NEW.headshots IS NULL THEN
                NEW.headshots := 0;
        END IF;
        IF NEW.airshots is NULL THEN
                NEW.airshots := 0;
        END IF;
        IF NEW.backstabs IS NULL THEN
                NEW.backstabs := 0;
        END IF;
        IF NEW.damage_dealt IS NULL THEN
                NEW.damage_dealt := 0;
        END IF;
        IF NEW.damage_taken IS NULL THEN
                NEW.damage_taken := 0;
        END IF;
        IF NEW.ap_small IS NULL THEN
                NEW.ap_small := 0;
        END IF;
        IF NEW.ap_medium IS NULL THEN
                NEW.ap_medium := 0;
        END IF;
        IF NEW.ap_large IS NULL THEN
                NEW.ap_large := 0;
        END IF;
        IF NEW.mk_small IS NULL THEN
                NEW.mk_small := 0;
        END IF;
        IF NEW.mk_medium IS NULL THEN
                NEW.mk_medium := 0;
        END IF;
        IF NEW.mk_large IS NULL THEN
                NEW.mk_large := 0;
        END IF;
        IF NEW.captures IS NULL THEN
                NEW.captures := 0;
        END IF;
        IF NEW.captures_blocked IS NULL THEN
                NEW.captures_blocked := 0;
        END IF;
        IF NEW.dominations IS NULL THEN
                NEW.dominations := 0;
        END IF;
        IF NEW.times_dominated IS NULL THEN
                NEW.times_dominated := 0;
        END IF;
        IF NEW.revenges IS NULL THEN
                NEW.revenges := 0;
        END IF;
        IF NEW.suicides IS NULL THEN
                NEW.suicides := 0;
        END IF;
        IF NEW.buildings_destroyed IS NULL THEN
                NEW.buildings_destroyed := 0;
        END IF;
        IF NEW.extinguishes IS NULL THEN
                NEW.extinguishes := 0;
        END IF;

        RETURN NEW;
END;
$_$ LANGUAGE 'plpgsql';
