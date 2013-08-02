<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <?php
        include 'static/header.html';

        require "../conf/ll_database.php";
        require "../conf/ll_config.php";
        require 'func/help_functions.php';

        if (!$ll_db)
            die("<title>500 Internal Server Error</title>");

        if (empty($_GET['id']))
            $invalid_player = true;
        else
        {
            $community_id = $_GET['id'];
            $invalid_player = false;

            $escaped_cid = pg_escape_string($community_id);

            $stat_query =   "SELECT SUM(kills) as kills, SUM(deaths) as deaths, SUM(assists) as assists, SUM(points) as points, 
                                    SUM(healing_done) as healing_done, SUM(healing_received) as healing_received, SUM(ubers_used) as ubers_used, SUM(ubers_lost) as ubers_lost, 
                                    SUM(headshots) as headshots, SUM(backstabs) as backstabs, SUM(damage_dealt) as damage_dealt, SUM(damage_taken) as damage_taken,
                                    SUM(captures) as captures, SUM(captures_blocked) as captures_blocked, 
                                    SUM(dominations) as dominations, SUM(revenges) as revenges, SUM(times_dominated) as times_dominated,
                                    SUM(ap_small) as ap_small, SUM(ap_medium) as ap_medium, SUM(ap_large) as ap_large,
                                    SUM(mk_small) as mk_small, SUM(mk_medium) as mk_medium, SUM(mk_large) as mk_large
                            FROM {$ll_config["tables"]["player_stats"]} WHERE steamid = '{$escaped_cid}'";

            $stat_result = pg_query($ll_db, $stat_query);

            if (!$stat_result)
            {
                $invalid_player = true;
            }
            else
            {
                /*$player_logs_query = "SELECT HOST(server_ip) as server_ip, server_port, numeric_id, log_name, map, live, tstamp 
                                      FROM {$ll_config["tables"]["log_index"]}
                                      JOIN {$ll_config["tables"]["player_details"]} ON {$ll_config["tables"]["player_details"]}.log_ident = {$ll_config["tables"]["log_index"]}.log_ident 
                                      WHERE steamid = '{$escaped_cid}'
                                      ORDER BY numeric_id DESC
                                      LIMIT {$ll_config["display"]["player_num_past"]}"; //get all the logs that a user has been in

                $player_logs_result = pg_query($ll_db, $player_logs_query);

                if (pg_num_rows($player_logs_result) > 0)
                    $player_logs = pg_fetch_all($player_logs_result);
                else
                    $player_logs = NULL;
                */

                $total_logs_query = "SELECT COUNT(log_ident) as total
                                    FROM {$ll_config["tables"]["player_details"]}
                                    WHERE steamid = '{$escaped_cid}'";

                $total_logs_result = pg_query($ll_db, $total_logs_query);

                if ($total_logs_result && pg_num_rows($total_logs_result) > 0)
                {
                    $total_logs_array = pg_fetch_array($total_logs_result, NULL, PGSQL_ASSOC);
                    $total_player_logs = $total_logs_array["total"];
                }
                else
                {
                    $total_player_logs = 0;
                }

                if (pg_num_rows($stat_result) > 0)
                    $pstat = pg_fetch_array($stat_result, NULL, PGSQL_ASSOC);
                else
                    $pstat = NULL;
            
                
                

                $class_stats_query =    "SELECT class, SUM(kills) as kills, SUM(deaths) as deaths, SUM(assists) as assists, SUM(points) as points, 
                                           SUM(healing_done) as healing_done, SUM(healing_received) as healing_received, SUM(ubers_used) as ubers_used, SUM(ubers_lost) as ubers_lost, 
                                           SUM(headshots) as headshots, SUM(backstabs) as backstabs, SUM(damage_dealt) as damage_dealt, SUM(damage_taken) as damage_taken,
                                           SUM(dominations) as dominations, SUM(revenges) as revenges
                                        FROM {$ll_config["tables"]["player_stats"]}
                                        WHERE class != 'UNKNOWN' AND steamid = '{$escaped_cid}'
                                        GROUP BY class";

                $class_results = pg_query($ll_db, $class_stats_query);

                $name_query =  "SELECT name 
                                FROM {$ll_config["tables"]["player_details"]} 
                                WHERE steamid = {$escaped_cid}
                                ORDER BY id DESC"; //get the most recently used name

                $name_result = pg_query($ll_db, $name_query);
                if (pg_num_rows($name_result) > 0)
                {
                    $name_array = pg_fetch_array($name_result, 0, PGSQL_ASSOC);
                    $player_name = $name_array["name"];
                }
                else
                {
                    $player_name = "LL_INVALID_STRING";
                }
            }
        }
    ?>

    <title>Livelogs - <?=htmlentities($player_name, ENT_QUOTES, "UTF-8")?>'s stats</title>

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
            if ($invalid_player)
            {
                die("404 player not found</div>");
            }
        ?>

        <div class="details_container">
            <span class="log_detail_id">Name:</span> <span><a href="//steamcommunity.com/profiles/<?=$community_id?>"><?=htmlentities($player_name, ENT_QUOTES, "UTF-8")?></a></span> <br>
            <span class="log_detail_id">Steam ID:</span> <span><?=big_int_to_steamid($community_id)?></span> <br>
        </div>

        <div class="stat_table_container">
            <table class="table table-bordered table-hover ll_table" id="general_stats">
                <thead>
                    <tr class="stat_summary_title_bar">
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
                            <abbr title="Damage Taken">DT</abbr>
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
                    </tr>
                </thead>
                <tbody>
                <?php
                    $p_kpd = round($pstat["kills"] / (($pstat["deaths"]) ? $pstat["deaths"] : 1), 2); // kills/death
                    //$p_ppd = round($pstat["points"] / $pstat["deaths"], 3); // points/death - useless statistic
                    //$p_apd = round($pstat["assists"] / $pstat["deaths"], 3); // assists/death - useless statistic
                    $p_dpd = round($pstat["damage_dealt"] / (($pstat["deaths"]) ? $pstat["deaths"] : 1), 2); //damage/death
                    
                    ?>
                    
                    <tr>
                        <td><?=$pstat["kills"]?></td>
                        <td><?=$pstat["deaths"]?></td>
                        <td><?=$pstat["assists"]?></td>
                        <td><?=$pstat["captures"]?></td>
                        <td><?=$pstat["captures_blocked"]?></td>
                        <td><?=$pstat["headshots"]?></td>
                        <td><?=$pstat["backstabs"]?></td>
                        <td><?=$pstat["points"]?></td>
                        <td><?=$pstat["damage_dealt"]?></td>
                        <td><?=$pstat["damage_taken"]?></td>
                        <td><?=$pstat["healing_received"]?></td>
                        <td><?=$pstat["dominations"]?></td>
                        <td><?=$pstat["times_dominated"]?></td>
                        <td><?=$pstat["revenges"]?></td>
                        <td><?=$p_kpd?></td>
                        <td><?=$p_dpd?></td>
                    </tr>
                </tbody>
                <caption>Overall stats</caption>
            </table>
        </div>

        <div class="stat_table_container">
            <table class="table table-bordered table-striped table-hover ll_table" id="class_stats">
                <thead>
                    <tr class="stat_summary_title_bar">
                        <th class="stat_summary_col_title">
                            <abbr title="Player's class">Class</abbr>
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
                            <abbr title="Damage Taken">DT</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Healing Received">HealR</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Dominations">DMN</abbr>
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
                    </tr>
                </thead>
                <tbody>
                <?php
                    /*class, kills, deaths, assists, points
                    healing_done, healing_received, ubers_used, ubers_lost,
                    headshots, backstabs, damage_dealt, damage_taken,
                    dominations, revenges
                    */
                    $mstat = 0;

                    while ($cstat = pg_fetch_array($class_results, NULL, PGSQL_ASSOC))
                    {
                        $p_kpd = round($cstat["kills"] / (($cstat["deaths"]) ? $cstat["deaths"] : 1), 2); // kills/death
                        $p_dpd = round($cstat["damage_dealt"] / (($cstat["deaths"]) ? $cstat["deaths"] : 1), 2); //damage/death
                    
                        if ($cstat["class"] === "medic")
                        {
                            $mstat = $cstat;
                        }
                    ?>
                    
                    <tr>
                        <td><?=player_classes($cstat["class"])?></td>
                        <td><?=$cstat["kills"]?></td>
                        <td><?=$cstat["deaths"]?></td>
                        <td><?=$cstat["assists"]?></td>
                        <td><?=$cstat["headshots"]?></td>
                        <td><?=$cstat["backstabs"]?></td>
                        <td><?=$cstat["points"]?></td>
                        <td><?=$cstat["damage_dealt"]?></td>
                        <td><?=$cstat["damage_taken"]?></td>
                        <td><?=$cstat["healing_received"]?></td>
                        <td><?=$cstat["dominations"]?></td>
                        <td><?=$cstat["revenges"]?></td>
                        <td><?=$p_kpd?></td>
                        <td><?=$p_dpd?></td>
                    </tr>
                    <?php
                    }
                    ?>
                    
                </tbody>
                <caption>Class stats</caption>
            </table>
        </div>

        <?php
        if ($mstat)
        {
        ?>

        <div class="stat_table_container stat_table_container_small">
            <table class="table table-bordered table-hover ll_table">
                <thead>
                    <tr class="stat_summary_title_bar">
                        <th>
                            Healing
                        </th>
                        <th>
                            Ubers Used
                        </th>
                        <th>
                            Ubers Lost
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><?=$mstat["healing_done"]?></td>
                        <td><?=$mstat["ubers_used"]?></td>
                        <td><?=$mstat["ubers_lost"]?></td>
                    </tr>
                </tbody>

                <caption>Medic stats</caption>
            </table>
        </div>
        <?php
        }
        ?>
        <div class="log_list_past_container">
            <?php
            //if (sizeof($player_logs) > 0)
            //{
            ?>
            <table class="table table-bordered table-hover table-striped ll_table" id="past_logs">
                <thead>
                    <tr class="stat_summary_title_bar info">
                        <th class="log_list_col_title">
                            Server IP
                        </th>
                        <th class="log_list_col_title">
                            Server Port
                        </th>
                        <th class="log_list_col_title">
                            Map
                        </th>
                        <th class="log_list_col_title">
                            Log Name
                        </th>
                        <th class="log_list_col_title">
                            Date
                        </th>
                    </tr>
                </thead>
                <tbody>

                </tbody>
                <caption>Past and current logs (<?=$total_player_logs?> found)</caption>
            </table>

            <?php
            //}
            ?>

        </div>

        <?php include('static/logo.html'); ?>

    </div>
    <?php include('static/footer.html'); ?>

    <script src="/js/playerview.js" type="text/javascript"></script>
    <script type="text/javascript">
        /*
        pass the steamid, number of logs shown and the total number of logs to the datatables init
        so that we can make this shit work
        */
        ll_paging.init("<?=$escaped_cid?>", <?=$ll_config["display"]["player_num_past"]?>);
    </script>

</body>
</html>

<?php
    pg_close($ll_db);
?>
