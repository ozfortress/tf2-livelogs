<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <?php
        include 'static/header.html';

        require "../conf/ll_database.php";
        require "../conf/ll_config.php";
        require 'func/help_functions.php';
        
        $log_serial = $_GET["lognum"];

        $escaped_serial = pg_escape_string($log_serial);
        
        $log_detail_query = "SELECT log_ident, log_name, server_ip, server_port, map, live, webtv_port, tstamp
                            FROM livelogs_log_index 
                            WHERE numeric_id = '{$escaped_serial}'";

        $log_detail_res = pg_query($ll_db, $log_detail_query);

        ////server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean
        $log_details = pg_fetch_array($log_detail_res, 0, PGSQL_ASSOC);
        
        if (empty($log_details["log_ident"]))
        {
            $invalid_log_ident = true;
        }
        else
        {
            //valid numeric id given. get log ident out
            $_unique_ident = $log_details["log_ident"];

            //live or not
            if ($log_details["live"] === "f")
                $log_live = false;
            else
                $log_live = true;

            if (function_exists("pg_escape_identifier"))
            {
                $escaped_event_table = pg_escape_identifier("log_event_" . $_unique_ident);
            }
            else
            {
                $escaped_event_table = pg_escape_string("log_event_" . $_unique_ident);
            }
            
            $stat_query =  "SELECT steamid, team, class,
                                    kills, deaths, assists, points, 
                                    healing_done, healing_received, ubers_used, ubers_lost, 
                                    headshots, damage_dealt, damage_taken,
                                    captures, captures_blocked, 
                                    dominations
                            FROM livelogs_player_stats
                            WHERE log_ident = '{$_unique_ident}'";

            $stat_result = pg_query($ll_db, $stat_query);

            $name_query =  "SELECT steamid, name 
                            FROM livelogs_player_details
                            WHERE log_ident = '{$_unique_ident}'";

            $name_result = pg_query($ll_db, $name_query);

            
            $chat_query = "SELECT steamid, name, team, chat_type, chat_message FROM livelogs_game_chat WHERE log_ident = '{$_unique_ident}'";
            $chat_result = pg_query($ll_db, $chat_query);

            if (!$log_live)
            {
                $time_query =  "SELECT event_time FROM {$escaped_event_table} WHERE eventid = '1' 
                                UNION 
                                SELECT event_time FROM {$escaped_event_table} WHERE eventid = (SELECT MAX(eventid) FROM {$escaped_event_table})";
            
                $time_result = pg_query($ll_db, $time_query);
                $time_array = pg_fetch_all($time_result);
            }

            if ((!$stat_result) || (!$chat_result) || (!$name_result))
            {
                echo "PGSQL HAD ERROR: " . pg_last_error();
            }
            
            $score_query = "SELECT COALESCE(round_red_score, 0) as red_score, COALESCE(round_blue_score, 0) as blue_score 
                            FROM {$escaped_event_table} WHERE round_red_score IS NOT NULL AND round_blue_score IS NOT NULL 
                            ORDER BY eventid DESC LIMIT 1";
                            
            $score_result = pg_query($ll_db, $score_query);
            if ($score_result && pg_num_rows($score_result) > 0)
            {
                $score_array = pg_fetch_array($score_result, 0);
                $red_score = $score_array["red_score"];
                $blue_score = $score_array["blue_score"];
            }
            else
            {
                $red_score = 0;
                $blue_score = 0;
            }

            $team_stats_query = "SELECT team, SUM(kills) as team_kills, SUM(deaths) AS team_deaths, 
                                SUM(healing_done) as team_healing_done, 
                                SUM(damage_dealt) as team_damage_dealt, SUM(damage_taken) as team_damage_taken
                                FROM livelogs_player_stats
                                WHERE log_ident = '{$_unique_ident}' and team IS NOT NULL
                                GROUP BY team";

            $team_stats_result = pg_query($ll_db, $team_stats_query);

            if ($log_live)
            {
                date_default_timezone_set("Australia/Melbourne");
                $time_start = $log_details["tstamp"]; //the time the log was created
                $time_start_ctime = strtotime($time_start); //time in format "2013-07-04 23:59:53"

                $curr_time = time();

                $time_elapsed_sec = $curr_time - $time_start_ctime;
            }
            else if (sizeof($time_array) == 2)
            {
                $time_start = $time_array[0]["event_time"]; //starting time
                $time_start_ctime = strtotime($time_start); //time is in format "10/01/2012 21:38:18"

                $time_last = $time_array[1]["event_time"]; //latest time in the log
                $time_last_ctime = strtotime($time_last); //time is in format "10/01/2012 21:38:18"

                $time_elapsed_sec = $time_last_ctime - $time_start_ctime;
            }
            else
            {
                $time_elapsed_sec = 0;
            }

            $time_elapsed = sprintf("%02d minute(s) and %02d second(s)", ($time_elapsed_sec/60)%60, $time_elapsed_sec%60);
            
            $invalid_log_ident = false;
        }
    ?>

    <title>Livelogs - <?=$log_details["log_name"]?> (<?=$_unique_ident?>)</title>
</head>
<body class="ll_body">
    <div class="navbar navbar-inverse navbar-fixed-top">
        <div class="navbar-inner">
            <div class="livelogs_nav_container">
                <img class="pull-left" src="/images/livelogs-beta.png">
                <ul class="nav">
                    <li>
                        <a href="/">Home</a>
                    </li>
                    <li>
                        <a href="/past">Archive</a>
                    </li>
                    <li>
                        <a href="/leaders">Leaderboard</a>
                    </li>
                    <li class="dropdown active">
                        <a class="dropdown-toggle" data-toggle="dropdown" href="#">View Settings <b class="caret"></b></a>
                        <ul class="dropdown-menu">
                            <li>
                                <a href="#" data-toggle="collapse" data-target="#chat_event_feed">Show Chat</a>
                            </li>
                            <?php 
                            if (($log_live) && ($log_details["webtv_port"]))
                            {
                            ?>
                            
                            <li>
                                <a href="#" data-toggle="collapse" data-target="#sourcetv2d">Show SourceTV 2D</a>
                            </li>
                            <?php
                            }
                            
                            if (($log_live) && (!empty($ll_config["websock"]["server_ip"])))
                            {
                            ?>
                            
                            <li>
                                <a href="javascript:llWSClient.toggleUpdate()">Auto Update Stats</a>
                            </li>
                            <?php
                            }
                            ?>
                            
                        </ul>
                    </li>
                </ul>
                <ul class="nav pull-right">
                    <li class="dropdown">
                        <a class="dropdown-toggle" data-toggle="dropdown" href="#">Help <b class="caret"></b></a>
                        <ul class="dropdown-menu">
                            <li>
                                <a href="#about_modal" data-toggle="modal">About</a>
                            </li>
                            
                            <li>
                                <a href="#faq_modal" data-toggle="modal">FAQ</a>
                            </li>
                            <li class="disabled">
                                <a href="#">Source</a>
                            </li>
                        </ul>
                    </li>
                    <li class="disabled">
                        <a href="#">Login</a>
                    </li>
                </ul>
            </div>
        </div>
    </div>
    <div class="livelogs_wrapper">
    <?php
    if ($invalid_log_ident)
    {
        die("404</div>"); //die with an error if we have invalid log ident and close the main div
    }
    ?>

        <div class="details_container">
        <?php
        if ($log_live) 
        {
        ?>
            
            <span class="log_detail_id">Log ID: </span><span class="log_detail"><a href="#"><?=$_unique_ident?></a></span><br>
        <?php
        }
        else
        {
            $log_split = explode("_", $_unique_ident);
        ?>
            
            <span class="log_detail_id">Log ID: </span><span class="log_detail"><a href="/download/<?=$_unique_ident?>"><?=$_unique_ident?></a></span><br>
            <span class="log_detail_id">Date: </span><span class="log_detail"><?=date("d/m/Y H:i:s", $log_split[2])?></span><br>
        <?php
        }

        if ($ll_config["ozfortress"]["active"])
        {
        ?>

            <span class="log_detail_id">Name: </span><span class="log_detail">
                <a href="<?=$ll_config["ozfortress"]["basepath"] . hash_hmac($ll_config["ozfortress"]["hashtype"], strtolower($log_details["log_name"]), $ll_config["ozfortress"]["hashkey"])?>"><?=$log_details["log_name"]?></a>
            </span><br>
        <?php
        }
        else 
        {
        ?>

            <span class="log_detail_id">Name: </span><span class="log_detail"><?=$log_details["log_name"]?></span><br>
        <?php
        }
        ?>

            
            <span class="log_detail_id">Server: </span><span class="log_detail"><?=long2ip($log_details["server_ip"])?>:<?=$log_details["server_port"]?></span><br>
            <span class="log_detail_id">Map: </span><span class="log_detail"><?=$log_details["map"]?></span><br>

            <div>
                <span class="log_detail_id">Status: </span>
            <?php
            if ($log_live)
            {
            ?>
            
                <span class="log_status text-success" id="log_status_span">Live!</span><br>
                <span class="log_detail_id">Time Elapsed: </span><span id="time_elapsed" class="log_detail"><?=$time_elapsed?></span><br><br>
            <?php
            }
            else
            {
            ?>
            
                <span class="log_status text-error" id="log_status_span">Complete</span><br>
                <span class="log_detail_id">Total Time: </span><span id="time_elapsed" class="log_detail"><?=$time_elapsed?></span><br><br>
            <?php
            }
            ?>
            
                <span class="red_score_tag">RED </span><span id="red_score_value" class="team_score_value"><?=(($red_score) ? $red_score : 0)?></span>
                <span class="blue_score_tag">BLUE </span><span id="blue_score_value" class="team_score_value"><?=(($blue_score) ? $blue_score : 0)?></span>
            </div>
        </div>

        <div class="stat_table_container">
            <table class="table table-bordered table-striped table-hover ll_table" id="general_stats">
                <thead>
                    <tr class="stat_summary_title_bar">
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
                            <abbr title="Points">PTS</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Damage Dealt">DMG</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Damage Taken">DT</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Healing Received">HR</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Dominations">DOM</abbr>
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
                        <th class="stat_summary_col_title">
                            <abbr title="Damage per Minute">DPM</abbr>
                        </th>
                    </tr>
                </thead>
                <tbody>
                <?php
                    /*
                    Stat table columns:
                        steamid, team, name, class,
                                kills, deaths, assists, points, 
                                healing_done, healing_received, ubers_used, ubers_lost, 
                                headshots, damage_dealt, damage_taken,
                                captures, captures_blocked, 
                                dominations
                     */

                    /*OLD COLS:
                    <td><span id="<?=$community_id . ".backstabs"?>"><?=$pstat["backstabs"]?></span></td>
                    <td><span id="<?=$community_id . ".t_dominated"?>"><?=$pstat["times_dominated"]?></span></td>
                    <td id="<?=$community_id . ".revenges"?>"><?=$pstat["revenges"]?></td>
                     */

                    $mstats = array();
                    //NAME:K:D:A:PC:PB:HS:PTS:DMG:DMGT:HEAL:DOM:R:KPD:DPD:DPR:DPM

                    if ($stat_result)
                    {
                        $stat_array = pg_fetch_all($stat_result);
                        $player_stats = merge_stat_array($stat_array);
                    }

                    if ($name_result)
                        $name_array = fetch_name_array($name_result);  

                    //while ($pstat = pg_fetch_array($stat_result, NULL, PGSQL_ASSOC))
                    foreach ($player_stats as $community_id => $pstat)
                    {
                        if (empty($name_array[$community_id]["name"]))
                        {
                            $p_name = "LL_INVALID_STRING";
                        }
                        else
                        {
                            $p_name = $name_array[$community_id]["name"];
                        }

                        $p_kpd = round($pstat["kills"] / (($pstat["deaths"]) ? $pstat["deaths"] : 1), 2); // kills/death
                        $p_dpd = round($pstat["damage_dealt"] / (($pstat["deaths"]) ? $pstat["deaths"] : 1), 2); //damage/death
                        $p_dpr = round($pstat["damage_dealt"] / (($red_score || $blue_score) ? ($red_score + $blue_score) : 1), 2); //num rounds are red score + blue score, damage/round
                        $p_dpm = round($pstat["damage_dealt"] / ($time_elapsed_sec/60), 2);


                        $team_class = get_player_team_class(strtolower($pstat["team"]));
                        
                        if (($pstat["healing_done"] > 0) || ($pstat["ubers_used"]) || ($pstat["ubers_lost"]))
                        {
                            $mstats[$community_id] = $pstat;
                            $mstats[$community_id]["name"] = $p_name;
                        }
                ?>
                    
                    <tr>
                        <td>
                            <span id="<?=$community_id . ".class"?>"><?=player_classes($pstat["class"])?></span>
                            <a id="<?=$community_id . ".name"?>" class="player_community_id_link <?=$team_class?>" href="/player/<?=$community_id?>"><?=htmlentities($p_name, ENT_QUOTES, "UTF-8")?></a>
                        </td>
                        <td id="<?=$community_id . ".kills"?>"><?=$pstat["kills"]?></td>
                        <td id="<?=$community_id . ".deaths"?>"><?=$pstat["deaths"]?></td>
                        <td id="<?=$community_id . ".assists"?>"><?=$pstat["assists"]?></td>
                        <td id="<?=$community_id . ".captures"?>"><?=$pstat["captures"]?></td>
                        <td id="<?=$community_id . ".captures_blocked"?>"><?=$pstat["captures_blocked"]?></td>
                        <td id="<?=$community_id . ".headshots"?>"><?=$pstat["headshots"]?></td>
                        <td id="<?=$community_id . ".points"?>"><?=$pstat["points"]?></td>
                        <td id="<?=$community_id . ".damage_dealt"?>"><?=$pstat["damage_dealt"]?></td>
                        <td id="<?=$community_id . ".damage_taken"?>"><?=empty($pstat["damage_taken"]) ? 0 : $pstat["damage_taken"]?></td>
                        <td id="<?=$community_id . ".healing_received"?>"><?=$pstat["healing_received"]?></td>
                        <td id="<?=$community_id . ".dominations"?>"><?=$pstat["dominations"]?></td>
                        <td id="<?=$community_id . ".kpd"?>"><?=$p_kpd?></td>
                        <td id="<?=$community_id . ".dpd"?>"><?=$p_dpd?></td>
                        <td id="<?=$community_id . ".dpr"?>"><?=$p_dpr?></td>
                        <td id="<?=$community_id . ".dpm"?>"><?=$p_dpm?></td>
                    </tr>
                <?php
                    }
                ?>
                    
                </tbody>
                <caption>Summary of player statistics</caption>
            </table>
        </div>

        <div class="stat_table_container stat_table_container_small">
            <div class="medic_stat_summary">
                <table class="table table-bordered table-striped table-hover ll_table" id="medic_stats">
                    <thead>
                        <tr class="stat_summary_title_bar">
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
                        foreach ($mstats as $community_id => $mstat)
                        {

                            $team_class = get_player_team_class(strtolower($mstat["team"]));
                        ?>
                        
                        <tr>
                            <td>
                                <a id="<?=$community_id . ".med_name"?>" class="player_community_id_link <?=$team_class?>" href="/player/<?=$community_id?>"><?=htmlentities($mstat["name"], ENT_QUOTES, "UTF-8")?></a>
                            </td>
                            <td id="<?=$community_id . ".healing_done"?>"><?=$mstat["healing_done"]?></td>
                            <td id="<?=$community_id . ".ubers_used"?>"><?=$mstat["ubers_used"]?></td>
                            <td id="<?=$community_id . ".ubers_lost"?>"><?=$mstat["ubers_lost"]?></td>
                        </tr>
                    <?php
                        }
                    ?>
                    
                    </tbody>
                    <caption>Summary of medic statistics</caption>
                </table>
            </div>
        </div>

        <div class="stat_table_container stat_table_container_small">
            <table class="table table-bordered table-hover ll_table" id="team_stats">
                <thead>
                    <tr class="stat_summary_title_bar">
                        <th class="stat_summary_col_title">
                            <abbr title="The team">Team</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Total team kills">K</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Total team deaths">D</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Total team healing done">HD</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Total team damage dealt">DMG</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Total team damage taken">DT</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Total team damage per minute">DPM</abbr>
                        </th>
                    </tr>
                </thead>
                <tbody>
                <?php
                    while ($tstat = pg_fetch_array($team_stats_result, NULL, PGSQL_ASSOC))
                    {
                        $team_dpm = round($tstat["team_damage_dealt"] / ($time_elapsed_sec/60), 2);

                        $team_class = sprintf("%s_score_tag %s", $tstat["team"], get_player_team_class(strtolower($tstat["team"])));
                ?>

                    <tr>
                        <td id="<?=$tstat["team"] . ".team"?>" class="<?=$team_class?>"><?=strtoupper($tstat["team"])?></td>
                        <td id="<?=$tstat["team"] . ".team_kills"?>"><?=$tstat["team_kills"]?></td>
                        <td id="<?=$tstat["team"] . ".team_deaths"?>"><?=$tstat["team_deaths"]?></td>
                        <td id="<?=$tstat["team"] . ".team_healing_done"?>"><?=$tstat["team_healing_done"]?></td>
                        <td id="<?=$tstat["team"] . ".team_damage_dealt"?>"><?=$tstat["team_damage_dealt"]?></td>
                        <td id="<?=$tstat["team"] . ".team_damage_taken"?>"><?=$tstat["team_damage_taken"]?></td>
                        <td id="<?=$tstat["team"] . ".team_dpm"?>"><?=$team_dpm?></td>
                    </tr>
                <?php
                    }
                ?>

                </tbody>
                <caption>Total team stats</caption>
            </table>
        </div>
        <?php

        if (($log_live) && ($log_details["webtv_port"]))
        {
        ?>
        
        <div class="sourcetv_container collapse in">
            <div class="sourcetv_controls">
                <p class="text-info">STV 2D</p>
                <button class="btn btn-success" onclick="SourceTV2D.connect('<?=long2ip($log_details["server_ip"])?>', <?=$log_details["webtv_port"]?>)">Connect</button>
                <button class="btn btn-danger" onclick="SourceTV2D.disconnect()">Disconnect</button>
                <div class="btn-group" data-toggle="buttons-checkbox">
                    <button class="btn btn-info" data-toggle="collapse" data-target="#sourcetv2d">Toggle STV</button>
                    <button class="btn" onclick="SourceTV2D.toggleNames()" id="stv_nametoggle">Toggle Names</button>
                </div>
            </div>
            
            <div id="sourcetv2d">
                <!--leave this blank, the sourcetv2d js will populate it on connect-->
            </div>
            
            <div id="debug">
            
            </div>
        </div>
        <?php
        }

        if (pg_num_rows($chat_result) > 0)
        {
        ?>

        <div class="live_feed_container accordion" id="chat_accordion">
            <div class="accordion-group">
                <div class="accordion-heading" align="center">
                    <a class="accordion-toggle" data-toggle="collapse" data-parent="#chat_accordion" href="#chat_event_feed">
                        Game Chat
                    </a>
                </div>
                <div class="collapse" id="chat_event_feed">
                    <table class="table table-bordered table-hover ll_table chat" id="chat_table">
                        <thead>
                            <tr>
                                <th>
                                    <abbr title="Player Name">Name</abbr>
                                </th>
                                <th>
                                    <abbr title="Player's message">Message</abbr>
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                        <?php
                        while ($pchat = pg_fetch_array($chat_result, NULL, PGSQL_ASSOC))
                        {
                            $community_id = $pchat["steamid"];

                            $team_class = get_player_team_class(strtolower($pchat["team"]));

                            $chat_type = $pchat["chat_type"];
                        ?>

                            <tr>
                                <td class="player_chat"><span class="<?=$team_class?>"><?=htmlentities($pchat["name"], ENT_QUOTES, "UTF-8")?></span></td>
                                <td><span class="player_chat">(<?=$chat_type?>)</span> <span class="player_chat_message"><?=htmlentities($pchat["chat_message"], ENT_QUOTES, "UTF-8")?></span></td>
                            </tr>
                        <?php
                        }

                        ?>

                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <?php
        }
        include('static/logo.html');
        ?>
    </div>
    <?php include('static/footer.html'); ?>

    <script src="/js/sprintf-0.7-beta1.js" type="text/javascript"></script>
    <script src="/js/viewlog.js" type="text/javascript"></script>
    <?php
    if ($log_live)
    {
    ?>
    
    <script type="text/javascript">
        llWSClient.init("<?=$ll_config["websock"]["server_ip"]?>", <?=$ll_config["websock"]["server_port"]?>, "<?=$_unique_ident?>")
    </script>
    <?php
    }
    ?>
    
    <script src="/js/sourcetv2d.js" type="text/javascript"></script>
</body>
</html>

<?php
    pg_close($ll_db)
?>
