<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <title>Livelogs - Archive</title>

    <?php
        include 'static/header.html';
        require "../conf/ll_database.php";
        require "../conf/ll_config.php";

        if (!empty($ll_config["display"]["archive_num"]))
        {
            $num_logs = $ll_config["display"]["archive_num"];
        }
        else
        {
            $num_logs = 40;
        }
        
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
                                ORDER BY numeric_id DESC LIMIT {$num_logs}";
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
                                ORDER BY numeric_id DESC LIMIT {$num_logs}";
            }
        }
        else
        {
            $past_query = "SELECT server_ip, server_port, log_ident, log_name, map 
                            FROM livelogs_servers 
                            WHERE live='false'
                            ORDER BY numeric_id DESC LIMIT {$num_logs}";
        }
        
        $past_res = pg_query($ll_db, $past_query);
    ?>

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
                    <li class="active">
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
        <div class="log_list_past_container">
            <form class="form-search" action="javascript:void(0);" id="search_form">
                <input type="text" class="pastlogs_searchfield" placeholder="Enter search term" id="search_field" value="<?=$filter?>">
                <button type="submit" class="btn" id="search_submit">Search</button>
            </form>
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
                        <td class="log_date"><?=date("d/m/Y H:i:s", $log_split[2])?></td>
                    </tr>
                <?php
                }
                ?>
                
                </tbody>
            </table>
        </div>

        <?php include('static/logo.html'); ?>
    </div>
    <?php include('static/footer.html'); ?>

    <script src="/js/bindWithDelay.js" type="text/javascript"></script>
    <script src="/js/logsearch.js" type="text/javascript"></script>
</body>

</html>

<?php
    pg_close($ll_db)
?>