<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type">
    
    <title>Livelogs DEV - SHOWLOG</title>

    <!--<link href="/favicon.ico" rel="shortcut icon">-->

    <link rel="stylesheet" type="text/css" href="/css/viewlog.css">
    <link rel="stylesheet" type="text/css" href="/css/bootstrap/bootstrap.css">
    <?php
        require "conf/ll_database.php"
    ?>

</head>
<body>
    <div class="log_view_wrapper">
        <div id="navigation" class="view_navbar">
            <ul class="nav nav-pills">
                <li>
                    <a href="/">Home</a>
                </li>
                <li class="dropdown active">
                    <a class="dropdown-toggle" data-toggle="dropdown" href="#">View Settings <b class="caret"></b></a>
                    <ul class="dropdown-menu">
                        <li>
                            <a href="#">Stream Chat</a>
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
    
        <div class="log_details">
        <?php
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
            
        ?>
            <span class="log_id_tag">Log ID: </span><span class="log_id"><a href="/download/<?=$UNIQUE_IDENT?>"><?=$UNIQUE_IDENT?></a></span><br>
            <span class="log_name_id">Name: </span><span class="log_name"><?=$log_details["log_name"]?></span><br>
            <span class="server_details_id">Server: </span><span class="server_details"><?=long2ip($log_details["server_ip"])?>:<?=$log_details["server_port"]?></span><br>
            <span class="log_map_id">Map: </span><span class="log_map"><?=$log_details["map"]?></span><br>
            <div class="live_or_not">
                <span class="live_id">Status: </span>
            <?php
                if ($log_details["live"])
                {
                ?>
                    <span class="log_live text-success">Live!</span>
                <?php
                }
                else
                {
                ?>
                    <span class="log_not_live text-error">Not live</span>
                <?php
                }
            ?>
            </div>
        </div>
        <div class="stat_table_container">
            <div class="table_header">
                <strong>INDIVIDUAL PLAYER STATISTICS</strong>
            </div>
            <div class="general_stat_summary">
                <table class="table table-bordered table-striped table-hover stat_table" id="general_stats" cellspacing="0" cellpadding="3" border="1">
                    <thead>
                        <tr class="stat_summary_title_bar info">
                            <th class="stat_summary_col_title">
                                Name
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Kills">K</abbr>
                            </th>
                            <th class="stat_summary_col_title">
                                <abbr title="Deaths">D</abbr>
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
                            <th class="stat_summary_col_title_secondary">
                                APD
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
                         
                        //NAME:K:D:A:P:DMG:HEAL:HS:BS:PC:PB:DMN:TDMN:R:KPD:APD:PPD:DPD:DPR
                        while ($pstat = pg_fetch_array($stat_result, NULL, PGSQL_BOTH))
                        {
                            $community_id = steamid_to_bigint($pstat["steamid"]);
                            $p_kpd = round($pstat["kills"] / $pstat["deaths"], 3); // kills/death
                            $p_ppd = round($pstat["points"] / $pstat["deaths"], 3); // points/death
                            $p_apd = round($pstat["assists"] / $pstat["deaths"], 3); // assists/death
                            $p_dpd = round($pstat["damage_dealt"] / $pstat["deaths"], 3); //damage/death
                            $p_dpr = 0; //we have no round summation yet!
                    ?>
                        <tr>
                            <td><a class="player_community_id_link" href="/player/<?=$community_id?>"><?=$pstat["name"]?></a></td>
                            <td><span id="<?=$community_id . kills?>"><?=$pstat["kills"]?></span></td>
                            <td><span id="<?=$community_id . deaths?>"><?=$pstat["deaths"]?></span></td>
                            <td><span id="<?=$community_id . assists?>"><?=$pstat["assists"]?></span></td>
                            <td><span id="<?=$community_id . points?>"><?=$pstat["points"]?></span></td>
                            <td><span id="<?=$community_id . damage?>"><?=$pstat["damage_dealt"]?></span></td>
                            <td><span id="<?=$community_id . heal_rcvd?>"><?=$pstat["healing_received"]?></span></td>
                            <td><span id="<?=$community_id . headshots?>"><?=$pstat["headshots"]?></span></td>
                            <td><span id="<?=$community_id . backstabs?>"><?=$pstat["backstabs"]?></span></td>
                            <td><span id="<?=$community_id . pointcaps?>"><?=$pstat["captures"]?></span></td>
                            <td><span id="<?=$community_id . pointblocks?>"><?=$pstat["captures_blocked"]?></span></td>
                            <td><span id="<?=$community_id . dominations?>"><?=$pstat["dominations"]?></span></td>
                            <td><span id="<?=$community_id . t_dominated?>"><?=$pstat["times_dominated"]?></span></td>
                            <td><span id="<?=$community_id . revenges?>"><?=$pstat["revenges"]?></span></td>
                            <td><span id="<?=$community_id . kpd?>"><?=$p_kpd?></span></td>
                            <td><span id="<?=$community_id . apd?>"><?=$p_apd?></span></td>
                            <td><span id="<?=$community_id . ppd?>"><?=$p_ppd?></span></td>
                            <td><span id="<?=$community_id . dpd?>"><?=$p_dpd?></span></td>
                            <td><span id="<?=$community_id . dpr?>"><?=$p_dpr?></span></td>
                        </tr>
                    <?php
                        }
                    ?>
                        
                    </tbody>
                    <caption>Summary of player statistics</caption>
                </table>
            </div>
        </div>
        <div class="event_feed_container">
        
        </div>
    </div>
    
    <script type="text/javascript">
        $(document).ready(function() 
        {
            $('#general_stats').dataTable( {
                "aaSorting": [[2, 'asc']]
                "bPaginate": false,
                "bAutoWidth": false;
                "bSortClasses": false,
                "bSearchable": true,
            } );
        } );
    </script>
    <!-- LOAD SCRIPTS AT THE BOTOM FOR PERFORMANCE ++ -->
    <!-- use local scripts for dev
    <script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js"></script>
    <script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.9.1/jquery-ui.min.js"></script>
    <script type="text/javascript" charset="utf8" src="http://ajax.aspnetcdn.com/ajax/jquery.dataTables/1.9.4/jquery.dataTables.min.js"></script>
    -->
    <script src="/js/jquery.min.js"></script>
    <script src="/js/jquery-ui.min.js"></script>
    <script src="/js/jquery.dataTables.min.js"></script>
    <script src="/js/bootstrap/bootstrap.js"></script>
    
    <script src="/js/viewlog.js"></script>
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
