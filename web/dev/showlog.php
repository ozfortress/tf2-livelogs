<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type">
    
    <title>Livelogs DEV - SHOWLOG</title>
    <?php
        require "conf/ll_database.php";
        
        $UNIQUE_IDENT = $_GET["ident"];
        $escaped_ident = pg_escape_string($UNIQUE_IDENT);
        
        $log_detail_query = "SELECT log_name, server_ip, server_port, map, live, webtv_port FROM livelogs_servers WHERE log_ident = '{$escaped_ident}'";
        $log_detail_res = pg_query($ll_db, $log_detail_query);

        ////server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean
        $log_details = pg_fetch_array($log_detail_res, 0, PGSQL_BOTH);
        
        if (!$log_details["log_name"])
        {
            $invalid_log_ident = true;
        }
        else
        {
            //have a valid ident. now we can grab stats and stuff!
            if (function_exists("pg_escape_identifier"))
            {
                $escaped_stat_table = pg_escape_identifier("log_stat_" . $UNIQUE_IDENT);
                $escaped_event_table = pg_escape_identifier("log_event_" . $UNIQUE_IDENT);
                $escaped_chat_table = pg_escape_identifier("log_chat_" . $UNIQUE_IDENT);
            }
            else
            {
                $escaped_stat_table = pg_escape_string("log_stat_" . $UNIQUE_IDENT);
                $escaped_event_table = pg_escape_string("log_event_" . $UNIQUE_IDENT);
                $escaped_chat_table = pg_escape_string("log_chat_" . $UNIQUE_IDENT);
            }
            
            $stat_query = "SELECT * FROM {$escaped_stat_table}";
            $stat_result = pg_query($ll_db, $stat_query);
            
            $event_query = "SELECT * FROM {$escaped_event_table}";
            $event_result = pg_query($ll_db, $event_query);
            
            $chat_query = "SELECT * FROM {$escaped_chat_table}";
            $chat_result = pg_query($ll_db, $chat_query);
            
            if ((!$stat_result) || (!$event_result) || (!$chat_result))
            {
                echo "PGSQL HAD ERROR: " . pg_last_error();
            }
            
            $score_query = "SELECT COALESCE(round_red_score, 0) as red_score, COALESCE(round_blue_score, 0) as blue_score 
                            FROM {$escaped_event_table} WHERE round_red_score IS NOT NULL AND round_blue_score IS NOT NULL 
                            ORDER BY eventid DESC LIMIT 1";
                            
            $score_result = pg_query($ll_db, $score_query);
            
            $score_array = pg_fetch_array($score_result, 0);
            $red_score = $score_array["red_score"];
            $blue_score = $score_array["blue_score"];
            
            $event_array = pg_fetch_all($event_result);
            $time_start = $event_array[0]["event_time"];
            $time_last = $event_array[(sizeof($event_array) - 1)]["event_time"];
            
            //time is in format "10/01/2012 21:38:18"
            $time_start_ctime = strtotime($time_start);
            $time_last_ctime = strtotime($time_last);
            
            $time_elapsed_sec = $time_last_ctime - $time_start_ctime;
            $time_elapsed = sprintf("%02d minute(s) and %02d second(s)", ($time_elapsed_sec/60)%60, $time_elapsed_sec%60);
            
            /*
            $time_query = "SELECT event_time as start_last_time FROM {$escaped_event_table} WHERE eventid = '1' UNION SELECT event_time FROM {$escaped_event_table} WHERE eventid = (SELECT MAX(eventid) FROM {$escaped_event_table})";
            $time_result = pg_query($ll_db, $time_query);
            
            $time_array = pg_fetch_array($time_result, 
            
            $time_elapsed = 0;*/
        }
        
        
        //live or not
        if ($log_details["live"] === "f")
            $log_live = false;
        else
            $log_live = true;
    ?>

    <!--<link href="/favicon.ico" rel="shortcut icon">-->
    <!--<link rel="stylesheet" type="text/css" href="http://ajax.aspnetcdn.com/ajax/jquery.dataTables/1.9.4/css/jquery.dataTables.css">-->
    <link rel="stylesheet" type="text/css" href="/css/jquery.dataTables.css">
    <link rel="stylesheet" type="text/css" href="/css/bootstrap/bootstrap.css">
    <link rel="stylesheet" type="text/css" href="/css/viewlog.css">
    
</head>
<body class="ll_body">
    <div class="livelogs_wrapper">
        <?php
        if ($invalid_log_ident)
        {
            die("404</div>"); //die with an error if we have invalid log ident, but close the main div
        }
        ?>
        <div id="navigation" class="ll_navbar">
            <ul class="nav nav-pills">
                <li>
                    <a href="/">Home</a>
                </li>
                <li class="dropdown">
                    <a class="dropdown-toggle" data-toggle="dropdown" href="#">View Settings <b class="caret"></b></a>
                    <ul class="dropdown-menu">
                        <li>
                            <a href="#">Show Chat</a>
                        </li>
                        <li<?if ((!$log_live) || (!$log_details["webtv_port"])) echo ' class="disabled"'?>>
                            <a href="#" data-toggle="collapse" data-target="#sourcetv2d">Show SourceTV 2D</a>
                        </li>
                        <li class="disabled">
                            <a href="#">Auto Update Stats</a>
                        </li>
                    </ul>
                </li>
                <li class="dropdown">
                    <a class="dropdown-toggle" data-toggle="dropdown" href="#">Help <b class="caret"></b></a>
                    <ul class="dropdown-menu">
                        <li>
                            <a href="#">About</a>
                        </li>
                        
                        <li>
                            <a href="#">FAQ</a>
                        </li>
                        <li class="disabled">
                            <a href="#">Source @ github</a>
                        </li>
                    </ul>
                </li>
                <li>
                    <a href="#">Login</a>
                </li>
            </ul>
        </div>

        <div class="log_details_container">
            <span class="log_id_tag">Log ID: </span><span class="log_detail"><a href="/download/<?=$UNIQUE_IDENT?>"><?=$UNIQUE_IDENT?></a></span><br>
            <span class="log_name_id">Name: </span><span class="log_detail"><?=$log_details["log_name"]?></span><br>
            <span class="server_details_id">Server: </span><span class="log_detail"><?=long2ip($log_details["server_ip"])?>:<?=$log_details["server_port"]?></span><br>
            <span class="log_map_id">Map: </span><span class="log_detail"><?=$log_details["map"]?></span><br>
            <div>
                <span class="live_id">Status: </span>
            <?php
            if ($log_live)
            {
            ?>
                <span class="log_status text-success">Live!</span><br>
                <span class="time_elapsed_id">Time Elapsed: </span><span class="log_detail" id="time_elasped"><?=$time_elapsed?></span><br><br>
            <?php
            }
            else
            {
            ?>
                <span class="log_status text-error">Not live</span><br>
                <span class="time_elapsed_id">Total Time: </span><span class="log_detail" id="time_elasped"><?=$time_elapsed?></span><br><br>
            <?php
            }
            ?>
                <span class="red_score_tag">RED </span><span class="red_score" id="red_score_value"><?=(($red_score) ? $red_score : 0)?></span>
                <span class="blue_score_tag">BLUE </span><span class="blue_score" id="blue_score_value"><?=(($blue_score) ? $blue_score : 0)?></span>
            </div>
        </div>
        
        <div class="stat_table_container">
            <div class="general_stat_summary">
                <table class="table table-bordered table-striped table-hover ll_table" id="general_stats">
                    <thead>
                        <tr class="stat_summary_title_bar info">
                            <th class="stat_summary_col_title">
                                <abbr title="Player Name">Name</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Kills">K</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Deaths">D</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Assists">A</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Points Captured">PC</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Point Captures Blocked">PB</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Headshots">HS</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Backstabs">BS</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Points">Points</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Damage Dealt">DMG</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Healing Received">HealR</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Dominations">DMN</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Times Dominated">TDMN</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Revenges">R</abbr>
                            </th>
                            <th class="stat_summary_col_title_secondary">
                                <abbr title="Kills per Death">KPD</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Damage Dealt per Death">DPD</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Damage per Round">DPR</abbr>
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
                         
                        $mstats = Array();
                        //NAME:K:D:A:P:DMG:HEAL:HS:BS:PC:PB:DMN:TDMN:R:KPD:DPD:DPR
                        while ($pstat = pg_fetch_array($stat_result, NULL, PGSQL_BOTH))
                        {
                            $community_id = steamid_to_bigint($pstat["steamid"]);
                            $p_kpd = round($pstat["kills"] / (($pstat["deaths"]) ? $pstat["deaths"] : 1), 2); // kills/death
                            //$p_ppd = round($pstat["points"] / $pstat["deaths"], 3); // points/death - useless statistic
                            //$p_apd = round($pstat["assists"] / $pstat["deaths"], 3); // assists/death - useless statistic
                            $p_dpd = round($pstat["damage_dealt"] / (($pstat["deaths"]) ? $pstat["deaths"] : 1), 2); //damage/death
                            $p_dpr = round($pstat["damage_dealt"] / (($red_score) ? ($red_score + $blue_score) : 1), 2); //num rounds are red score + blue score, damage/round
                            
                            if (($pstat["healing_done"] > 0) || ($pstat["ubers_used"]) || ($pstat["ubers_lost"]))
                            {
                                $mstats[sizeof($mstats)] = $pstat;
                            }
                    ?>
                        <tr>
                            <td><a class="player_community_id_link" href="/player/<?=$community_id?>"><?=$pstat["name"]?></a></td>
                            <td><span id="<?=$community_id . ".kills"?>"><?=$pstat["kills"]?></span></td>
                            <td><span id="<?=$community_id . ".deaths"?>"><?=$pstat["deaths"]?></span></td>
                            <td><span id="<?=$community_id . ".assists"?>"><?=$pstat["assists"]?></span></td>
                            <td><span id="<?=$community_id . ".pointcaps"?>"><?=$pstat["captures"]?></span></td>
                            <td><span id="<?=$community_id . ".pointblocks"?>"><?=$pstat["captures_blocked"]?></span></td>
                            <td><span id="<?=$community_id . ".headshots"?>"><?=$pstat["headshots"]?></span></td>
                            <td><span id="<?=$community_id . ".backstabs"?>"><?=$pstat["backstabs"]?></span></td>
                            <td><span id="<?=$community_id . ".points"?>"><?=$pstat["points"]?></span></td>
                            <td><span id="<?=$community_id . ".damage"?>"><?=$pstat["damage_dealt"]?></span></td>
                            <td><span id="<?=$community_id . ".heal_rcvd"?>"><?=$pstat["healing_received"]?></span></td>
                            <td><span id="<?=$community_id . ".dominations"?>"><?=$pstat["dominations"]?></span></td>
                            <td><span id="<?=$community_id . ".t_dominated"?>"><?=$pstat["times_dominated"]?></span></td>
                            <td><span id="<?=$community_id . ".revenges"?>"><?=$pstat["revenges"]?></span></td>
                            <td><span id="<?=$community_id . ".kpd"?>"><?=$p_kpd?></span></td>
                            <td><span id="<?=$community_id . ".dpd"?>"><?=$p_dpd?></span></td>
                            <td><span id="<?=$community_id . ".dpr"?>"><?=$p_dpr?></span></td>
                        </tr>
                    <?php
                        }
                    ?>
                        
                    </tbody>
                    <caption>Summary of player statistics</caption>
                </table>
            </div>
        </div>
        <div class="left_float_feed_medic_container">
            <div class="stat_table_container stat_table_container_medic">
                <div class="medic_stat_summary">
                    <table class="table table-bordered table-striped table-hover ll_table" id="medic_stats">
                        <thead>
                            <tr class="stat_summary_title_bar info">
                                <th class="stat_summary_col_title">
                                    <abbr title="Player Name">Name</abbr>
                                </th>
                                <th class="stat_summary_col_title">
                                    <abbr title="Healing Done">Healing</abbr>
                                </th>
                                <th class="stat_summary_col_title">
                                    <abbr title="Ubers Used">U</abbr>
                                </th>
                                <th class="stat_summary_col_title">
                                    <abbr title="Ubers Lost">UL</abbr>
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                        <?php
                            $num_med = sizeof($mstats);
                            $i = 0;
                            
                            while ($i < $num_med)
                            {
                                $community_id = steamid_to_bigint($mstats[$i]["steamid"]);
                            ?>
                            <tr>
                                <td><a class="player_community_id_link" href="/player/<?=$community_id?>"><?=$mstats[$i]["name"]?></a></td>
                                <td><span id="<?=$community_id . ".heal_done"?>"><?=$mstats[$i]["healing_done"]?></span></td>
                                <td><span id="<?=$community_id . ".ubers_used"?>"><?=$mstats[$i]["ubers_used"]?></span></td>
                                <td><span id="<?=$community_id . ".ubers_lost"?>"><?=$mstats[$i]["ubers_lost"]?></span></td>
                            </tr>
                        <?php
                                $i++;
                            }
                        ?>
                        </tbody>
                        <caption>Summary of medic statistics</caption>
                    </table>
                </div>
            </div>
            
            <div class="live_feed_container">
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
                chat/event feed<br>
            </div>
        </div>
        
        <div class="left_float_sourcetv_container collapse in"<?if ((!$log_live) || (!$log_details["webtv_port"])) echo ' style="display: none;"'?>>
            <div class="sourcetv_controls">
                <p class="text-info">STV 2D</p>
                <button class="btn btn-success" onclick="stv2d_connect('<?=long2ip($log_details["server_ip"])?>', <?=$log_details["webtv_port"]?>)">Connect</button>
                <button class="btn btn-danger" onclick="stv2d_disconnect()">Disconnect</button>
                <div class="btn-group" data-toggle="buttons-checkbox">
                    <button class="btn btn-info" data-toggle="collapse" data-target="#sourcetv2d">Toggle STV</button>
                    <button class="btn" onclick="stv2d_togglenames()">Toggle Names</button>
                </div>
            </div>
            
            <div id="sourcetv2d">
                <!--leave this blank, the sourcetv2d js will populate it on connect-->
            </div>
            
            <div id="debug">
            
            </div>
        </div>
    </div>
        
    <!-- LOAD SCRIPTS AT THE BOTOM FOR PERFORMANCE ++ -->
    <!-- use local scripts for dev
    <script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js"></script>
    <script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.9.1/jquery-ui.min.js"></script>
    <script type="text/javascript" charset="utf8" src="http://ajax.aspnetcdn.com/ajax/jquery.dataTables/1.9.4/jquery.dataTables.min.js"></script>
    -->
    <script src="/js/jquery.min.js" type="text/javascript"></script>
    <script src="/js/jquery-ui.min.js" type="text/javascript"></script>
    <script src="/js/jquery.dataTables.min.js" type="text/javascript"></script>
    <script src="/js/bootstrap/bootstrap.js" type="text/javascript"></script>
    
    <script src="/js/viewlog.js" type="text/javascript"></script>
    <script src="/js/sourcetv2d.js" type="text/javascript"></script>
</body>
</html>

<?php
    function steamid_to_bigint($steamid)
    {
        //from Seather @ https://forums.alliedmods.net/showpost.php?p=565979&postcount=16
        //Used in https://www.gamealphamoreecho.com/steamidconverter
    
        $iServer = "0";
        $iAuthID = "0";
        
        $szAuthID = $steamid;
        
        $szTmp = strtok($szAuthID, ":");
        
        while(($szTmp = strtok(":")) !== false)
        {
            $szTmp2 = strtok(":");
            if($szTmp2 !== false)
            {
                $iServer = $szTmp;
                $iAuthID = $szTmp2;
            }
        }
        if($iAuthID == "0")
            return "0";

        $i64friendID = bcmul($iAuthID, "2");

        //Friend ID's with even numbers are the 0 auth server.
        //Friend ID's with odd numbers are the 1 auth server.
        $i64friendID = bcadd($i64friendID, bcadd("76561197960265728", $iServer)); 
        
        return $i64friendID;
    }

    pg_close($ll_db)
?>
