<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type">
    
    <title>Livelogs DEV</title>

    <!--<link href="/favicon.ico" rel="shortcut icon">-->
    <!--<link rel="stylesheet" type="text/css" href="http://ajax.aspnetcdn.com/ajax/jquery.dataTables/1.9.4/css/jquery.dataTables.css">-->
    <link rel="stylesheet" type="text/css" href="/css/jquery.dataTables.css">
    <link rel="stylesheet" type="text/css" href="/css/bootstrap/bootstrap.css">
    <link rel="stylesheet" type="text/css" href="/css/viewlog.css">

    <?php
        require "conf/ll_database.php"
    ?>

</head>
<body>
    <div class="wrapper">
        <div id="navigation" class="view_navbar">
            <ul class="nav nav-pills">
                <li class="active">
                    <a href="/">Home</a>
                </li>
                <li class="dropdown">
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
        <?php
            if (!$ll_db)
            {
                die("Unable to connect to database");
            }
        
            $live_query = "SELECT * FROM livelogs_servers WHERE live='true' ORDER BY numeric_id DESC";
            $live_res = pg_query($ll_db, $live_query);
        
            $past_query = "SELECT * FROM livelogs_servers WHERE live='false' ORDER BY numeric_id DESC LIMIT 10";
            $past_res = pg_query($ll_db, $past_query);
        
        ?>
        
        
        <div class="header">
            <p>HI!</p>
        </div>

        <div class="live_now">
        <?php
            if (!$live_res)
            {
            ?>
                <p class="text-error">Unable to retrieve live status</p>
            <?php
            }
            else
            {
            
            ?>
        <div class="live_log_list">
            <table width="100%">
                <thead>
                    <tr>
                        <th class="live_list_col_title">
                            Server IP
                        </th>
                        <th class="live_list_col_title">
                            Server Port
                        </th>
                        <th class="live_list_col_title">
                            Map
                        </th>
                        <th class="live_list_col_title">
                            Log Name
                        </th>
                    </tr>
                </thead>
                <tbody>
            <?php
                while ($live = pg_fetch_array($live_res, NULL, PGSQL_BOTH))
                {
                //server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean
                ?>
                    <tr>
                        <td class="server_ip"><?=long2ip($live["server_ip"])?></td>
                        <td class="server_port"><?=$live["server_port"]?></td>
                        <td class="log_map"><?=$live["map"]?></td>
                        <td class="log_name"><a href="/view/<?=$live["log_ident"]?>"><?=$live["log_name"]?></a></td>

                    </tr>
                <?php
                }
                ?>
                </tbody>
                <caption>Logs that are currently live</caption>
            </table>
        </div>
        <?php
            }
        ?>
        </div>
        <div class="past_logs">
        <?php
            if (!$past_res)
            {
            ?>
                <p class="text-error">Unable to retrieve past logs</p>
            <?php
            }
            else
            {
            
            ?>
        <div class="past_log_list">
            <table width="100%">
                <thead>
                    <tr>
                        <th class="live_list_col_title">
                            Server IP
                        </th>
                        <th class="live_list_col_title">
                            Server Port
                        </th>
                        <th class="live_list_col_title">
                            Map
                        </th>
                        <th class="live_list_col_title">
                            Log Name
                        </th>
                    </tr>
                </thead>
                <tbody>
            <?php
                while ($live = pg_fetch_array($past_res, NULL, PGSQL_BOTH))
                {
                //server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean
                ?>
                    <tr>
                        <td class="server_ip"><?=long2ip($live["server_ip"])?></td>
                        <td class="server_port"><?=$live["server_port"]?></td>
                        <td class="log_map"><?=$live["map"]?></td>
                        <td class="log_name"><a href="/view/<?=$live["log_ident"]?>"><?=$live["log_name"]?></a></td>

                    </tr>
                <?php
                }
                ?>
                </tbody>
                <caption>Past 10 Logs</caption>
            </table>
        </div>
        <?php
            }
        ?>
        </div>
        <div class="uploaded_logs">
        
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
    
</body>

</html>

<?php
    pg_close($ll_db)
?>
