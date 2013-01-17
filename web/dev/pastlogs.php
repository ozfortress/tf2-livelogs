<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type">
    
    <title>Livelogs DEV - PASTLOGS</title>

    <!--<link href="/favicon.ico" rel="shortcut icon">-->
    <!--<link rel="stylesheet" type="text/css" href="http://ajax.aspnetcdn.com/ajax/jquery.dataTables/1.9.4/css/jquery.dataTables.css">-->
    <link rel="stylesheet" type="text/css" href="/css/jquery.dataTables.css">
    <link rel="stylesheet" type="text/css" href="/css/bootstrap/bootstrap.css">
    <link rel="stylesheet" type="text/css" href="/css/livelogs.css">

    <?php
        require "../conf/ll_database.php";
        
        if (!$ll_db)
        {
            die("Unable to connect to database");
        }
        if (empty($_GET["filter"]))
            $filter = null;
        else
            $filter = str_replace("/", "", $_GET["filter"]);
        
        if ($filter)
        {
            $split_filter = explode(":", $filter);
            
            if (sizeof($split_filter) == 2)
            {
                //we most likely have an ip:port search
                $escaped_address = pg_escape_string(ip2long($split_filter[0]));
                $escaped_port = pg_escape_string((int)$split_filter[1]);
                
                $past_query = "SELECT server_ip, server_port, log_ident, log_name, map 
                                FROM livelogs_servers 
                                WHERE (server_ip = '{$escaped_address}' AND server_port = CAST('{$escaped_port}' AS INT))
                                ORDER BY numeric_id DESC LIMIT 40";
            }
            else
            {
                $longip = ip2long($filter);
        
                if ($longip)
                {
                    $escaped_filter = pg_escape_string($longip);
                }
                else
                {
                    $escaped_filter = pg_escape_string($filter);
                }
            
                $past_query = "SELECT server_ip, server_port, log_ident, log_name, map 
                                FROM livelogs_servers 
                                WHERE (server_ip ~* '{$escaped_filter}' OR log_name ~* '{$escaped_filter}' OR map ~* '{$escaped_filter}')
                                ORDER BY numeric_id DESC LIMIT 40";
            }
        }
        else
        {
            $past_query = "SELECT server_ip, server_port, log_ident, log_name, map FROM livelogs_servers WHERE live='false' AND numeric_id <= ((SELECT MAX(numeric_id) FROM livelogs_servers) - 10)
                            ORDER BY numeric_id DESC LIMIT 40";
        }
        
        $past_res = pg_query($ll_db, $past_query);
    ?>

</head>
<body class="ll_body">
    <div class="livelogs_wrapper">
        <div id="navigation" class="ll_navbar">
            <ul class="nav nav-pills">
                <li class="active">
                    <a href="/">Home</a>
                </li>
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
                <li>
                    <a href="#">Login</a>
                </li>
            </ul>
        </div>
        
        <div class="log_list_container">
            <div class="log_list">
                <input type="text" class="pastlogs_searchfield" placeholder="Enter search term" id="searchField" value="<?=$filter?>">
                <table class="table table-bordered table-hover ll_table">
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
                    <tbody id="pastLogs">
                    <?php
                    while ($log = pg_fetch_array($past_res, NULL, PGSQL_ASSOC))
                    {
                        $log_split = explode("_", $log["log_ident"]); //3232244481_27015_1356076576
                    ?>
                        
                        <tr>
                            <td class="server_ip"><?=long2ip($log["server_ip"])?></td>
                            <td class="server_port"><?=$log["server_port"]?></td>
                            <td class="log_map"><?=$log["map"]?></td>
                            <td class="log_name"><a href="/view/<?=$log["log_ident"]?>"><?=$log["log_name"]?></a></td>
                            <td class="log_date"><?=date("d/m/Y   H:i:s", $log_split[2])?></td>
                        </tr>
                    <?php
                    }
                    ?>
                    
                    </tbody>
                </table>
            </div>
        </div>
    </div>



    <!--BEGIN MODAL DIVS-->
    <div id="about_modal" class="modal hide fade" tabindex="-1" role="dialog" aria-labelledby="aboutModalLabel" aria-hidden="true">
        <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal" aria-hidden="true">x</button>
            <h3 id="aboutModelLabel">About Livelogs</h3>
        </div>

        <div class="modal-body">
            Nothing to see
        </div>

        <div class="modal-footer">
            <button class="btn" data-dismiss="modal" aria-hidden="true">Close</button>
        </div>
    </div>

    <div id="faq_modal" class="modal hide fade" tabindex="-1" role="dialog" aria-labelledby="faqModalLabel" aria-hidden="true">
        <div class="modal-header">
            <button type="button" class="close" data-dismiss="modal" aria-hidden="true">x</button>
            <h3 id="faqModelLabel">Frequently Asked Questions</h3>
        </div>

        <div class="modal-body">
            Empty
        </div>

        <div class="modal-footer">
            <button class="btn" data-dismiss="modal" aria-hidden="true">Close</button>
        </div>
    </div>

    <!-- LOAD SCRIPTS AT THE BOTOM FOR PERFORMANCE ++ -->
    <!-- use locally hosted scripts for dev 
    <script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.2/jquery.min.js"></script>
    <script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.9.1/jquery-ui.min.js"></script>
    <script type="text/javascript" charset="utf8" src="http://ajax.aspnetcdn.com/ajax/jquery.dataTables/1.9.4/jquery.dataTables.min.js"></script>
    -->
    <script src="/js/jquery.min.js"></script>
    <script src="/js/jquery-ui.min.js"></script>
    <script src="/js/jquery.dataTables.min.js"></script>
    <script src="/js/bootstrap/bootstrap.js" type="text/javascript"></script>
    <script src="/js/logsearch.js" type="text/javascript"></script>
</body>

</html>

<?php
    pg_close($ll_db)
?>