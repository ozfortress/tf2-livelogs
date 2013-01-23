<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <?php
        include 'static/header.html';
        require "../conf/ll_database.php";
        require "../conf/ll_config.php";

        if (!$ll_db)
            die("Unable to connect to database");

        if (empty($_GET['id']))
            $invalid_player = true;
        else
        {
            $community_id = $_GET['id'];
            $invalid_player = false;

            $steamid = big_int_to_steamid($community_id);

            $escaped_steamid = pg_escape_string($steamid);

            $stat_query = "SELECT * FROM livelogs_player_stats WHERE steamid='{$escaped_steamid}'";
            $stat_result = pg_query($ll_db, $stat_query);

            $pstat = pg_fetch_array($stat_result, NULL, PGSQL_ASSOC);
        }
    ?>

    <title>Livelogs - <?=$pstat["name"]?>'s stats</title>

</head>
<body class="ll_body">
    <div class="navbar navbar-inverse navbar-fixed-top">
        <div class="navbar-inner">
            <div class="livelogs_nav_container">
                <img class="pull-left" src="/images/livelogs-beta.png"></img>
                <ul class="nav">
                    <li>
                        <a href="/">Home</a>
                    </li>
                    <li>
                        <a href="/past">Archive</a>
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

        <div class="player_details_container">
            <span class="log_name_id">Name:</span> <span><a href="//steamcommunity.com/profiles/<?=$community_id?>"><?=$pstat["name"]?></a></span> <br>
            <span class="log_name_id">Steam ID:</span> <span><?=$steamid?></span> <br>
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
                        <th class="stat_summary_col_title">
                            <abbr title="Buildings Destroyed">BD</abbr>
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
                     
                    //NAME:K:D:A:P:DMG:HEAL:HS:BS:PC:PB:DMN:TDMN:R:KPD:DPD:DPR
                    $p_kpd = round($pstat["kills"] / (($pstat["deaths"]) ? $pstat["deaths"] : 1), 2); // kills/death
                    //$p_ppd = round($pstat["points"] / $pstat["deaths"], 3); // points/death - useless statistic
                    //$p_apd = round($pstat["assists"] / $pstat["deaths"], 3); // assists/death - useless statistic
                    $p_dpd = round($pstat["damage_dealt"] / (($pstat["deaths"]) ? $pstat["deaths"] : 1), 2); //damage/death
                    
                    ?>
                    
                    <tr>
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
                        <td><span><?=$pstat["buildings_destroyed"]?></span></td>
                        <td><span id="<?=$community_id . ".kpd"?>"><?=$p_kpd?></span></td>
                        <td><span id="<?=$community_id . ".dpd"?>"><?=$p_dpd?></span></td>
                    </tr>
                    
                </tbody>
                <caption>Player stats</caption>
            </table>
        </div>

        <div class="stat_table_container stat_table_container_small">
            <?php
            if (($pstat["healing_done"] > 0) || ($pstat["ubers_used"]) || ($pstat["ubers_lost"])) 
            {
            ?>

            <table class="table table-bordered table-hover ll_table">
                <thead>
                    <tr>
                        <th class="stat_summary_col_title">
                            <abbr title="Healing Done">Healing</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Ubers Used">Ubers</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Ubers Lost">UL</abbr>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><?=$pstat["healing_done"]?></td>
                        <td><?=$pstat["ubers_used"]?></td>
                        <td><?=$pstat["ubers_lost"]?></td>
                    </tr>
                </tbody>
                <caption>Player medic stats</caption>
            </table>
            <?php
            }
            ?>
            <table class="table table-bordered table-hover ll_table">
                <thead>
                    <tr>
                        <th class="stat_summary_col_title">
                            <abbr title="Medkit (Small)">MK S</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Medkit (Medium)">MK M</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Medkit (Large)">MK L</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Ammo pack (Small)">AP S</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Ammo pack (Medium)">AP M</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Ammo pack (Large)">AP L</abbr>
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><?=$pstat["mk_small"]?></td>
                        <td><?=$pstat["mk_medium"]?></td>
                        <td><?=$pstat["mk_large"]?></td>
                        <td><?=$pstat["ap_small"]?></td>
                        <td><?=$pstat["ap_medium"]?></td>
                        <td><?=$pstat["ap_large"]?></td>
                    </tr>
                </tbody>
                <caption>Total item pickups</caption>
            </table>
        </div>

        <?php include('static/logo.html'); ?>

    </div>
    <?php include('static/footer.html'); ?>

</body>
</html>

<?php
    function big_int_to_steamid($cid) {
        //converts a community id to a steamid
        $cid = $cid - 76561197960265728;
        $cid_half = $cid / 2;

        if ($cid % 2) //if there's a remainder, auth server is server 1, else it's server 0
        {
            $auth_server = 1;
            $steamid = $cid_half - 0.5;

            $steamid = sprintf("STEAM_0:%d:%d", $auth_server, $steamid);
        }
        else
        {
            $auth_server = 0;
            $steamid = sprintf("STEAM_0:%d:%d", $auth_server, $cid_half);
        }

        return $steamid;
    }

    pg_close($ll_db);
?>