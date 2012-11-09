<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en" xml:lang="en">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type">
    
    <title>Livelogs DEV - SHOWLOG</title>

    <!--<link href="/favicon.ico" rel="shortcut icon">-->

    <?php
        require "conf/ll_database.php"
    ?>

</head>
<body>
    <div class="wrapper">
        <div class="log_details">
        <?php
            echo $_GET['ident'] . " <br><br>";
            $UNIQUE_IDENT = $_GET["ident"];
            $escaped_ident = pg_escape_string($UNIQUE_IDENT);
            
            $log_detail_query = "SELECT log_name, server_ip, server_port, map, live FROM livelogs_servers WHERE log_ident = '{$escaped_ident}'";
            $log_detail_res = pg_query($ll_db, $log_detail_query);

            ////server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean
            $log_details = pg_fetch_array($log_detail_res, 0, PGSQL_BOTH);
            if (!$log_details["log_name"])
            {
                die("404");
            }
            
            //have a valid ident. now we can grab stats and stuff!
            
            $escaped_stat_table = pg_escape_string("log_stat_" . $UNIQUE_IDENT);
            $escaped_event_table = pg_escape_string("log_event_" . $UNIQUE_IDENT);
            $escaped_chat_table = pg_escape_string("log_chat_" . $UNIQUE_IDENT);
        ?>
            <span class="log_name_id">Name: </span><span class="log_name"><?=$log_details["log_name"]?></span><br>
            <span class="server_details_id">Server: </span><span class="server_details"><?=long2ip($log_details["server_ip"])?>:<?=$log_details["server_port"]?></span><br>
            <span class="log_map_id">Map: </span><span class="log_map"><?=$log_details["map"]?></span>
            <div class="live_or_not">
                <span class="live_id">Status: </span>
            <?php
                if ($log_details["live"])
                {
                ?>
                    <span class="log_live">Live!</span>
                <?php
                }
                else
                {
                ?>
                    <span class="log_not_live">Not live</span>
                <?php
                }
            ?>
            </div>
        </div>
        <div class="stat_table_container">
            <div class="table_header">
            </div>
            <div class="general_stat_summary">
                <table class="stat_table" id="general_stats" cellspacing="0" cellpadding="3" border="0">
                    <thead>
                        <tr>
                            <th class="stat_summary_col_title">
                                Name
                            </th>
                            <th class="stat_summary_col_title">
                                K
                            </th>
                            <th class="stat_summary_col_title">
                                D
                            </th>
                            <th class="stat_summary_col_title">
                                A
                            </th>
                            <th class="stat_summary_col_title">
                                P
                            </th>
                            <th class="stat_summary_col_title">
                                DMG
                            </th>
                            <th class="stat_summary_col_title">
                                HEAL
                            </th>
                            <th class="stat_summary_col_title">
                                HS
                            </th>
                            <th class="stat_summary_col_title">
                                BS
                            </th>
                            <th class="stat_summary_col_title">
                                PC
                            </th>
                            <th class="stat_summary_col_title">
                                PB
                            </th>
                            <th class="stat_summary_col_title">
                                DMN
                            </th>
                            <th class="stat_summary_col_title">
                                TDMN
                            </th>
                            <th class="stat_summary_col_title">
                                R
                            </th>
                            <th class="stat_summary_col_title_secondary">
                                KPD
                            </th>
                            <th class="stat_summary_col_title">
                                PPD
                            </th>
                            <th class="stat_summary_col_title">
                                DPD
                            </th>
                            <th class="stat_summary_col_title">
                                DPR
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                    <?php
                        /*
                        Stat table columns: (steamid varchar(64) PRIMARY KEY, name text, kills integer, deaths integer, assists integer, points decimal, 
					     healing_done integer, healing_received integer, ubers_used integer, ubers_lost integer, 
					     headshots integer, backstabs integer, damage_dealt integer, 
					     ap_small integer, ap_medium integer, ap_large integer,
					     mk_small integer, mk_medium integer, mk_large integer, 
					     captures integer, captures_blocked integer, 
					     dominations integer, times_dominated integer, revenges integer,
					     suicides integer, buildings_destroyed integer, extinguishes integer, kill_streak integer)'
                         */
                         
                        
                    ?>
                        <tr>asdf</tr>
                    </tbody>
                </table>
            </div>
        </div>
        <div class="event_feed">
        
        </div>
    </div>
    <!-- LOAD SCRIPTS AT THE BOTOM FOR PERFORMANCE ++ -->
    <!-- use local scripts for dev
    <script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js"></script>
    <script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.9.1/jquery-ui.min.js"></script>
    <script type="text/javascript" charset="utf8" src="http://ajax.aspnetcdn.com/ajax/jquery.dataTables/1.9.4/jquery.dataTables.min.js"></script>
    -->
    <script src="scripts/jquery.min.js"></script>
    <script src="scripts/jquery-ui.min.js"></script>
    <script src="scripts/jquery.dataTables.min.js"></script>
    
    <script src="scripts/viewlog.js"></script>
</body>
</html>

<?php
    pg_close($ll_db)
?>
