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
        <div class="header">
            <p>HI!</p>
        </div>

        <div class="live_now">
        <?php
            if (!$ll_db)
            {
                echo "Unable to connect to database";
            }
            else
            {
                $live_query = "SELECT * FROM livelogs_servers WHERE live='true'";
                $res = pg_query($ll_db, $live_query);

                if (!$res)
                {
                ?>
                    <p>Unable to retrieve live status</p>
                <?php
                }
                else
                {
                    while ($live = pg_fetch_array($res, NULL, PGSQL_BOTH))
                    {
                    //server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean
                    ?>
                    <div class="live_list">
                        <table width="100%">
                            <tr>
                                <td class="server_ip"><?=long2ip($live["server_ip"])?></td>
                                <td class="server_port"><?=$live["server_port"]?></td>
                                <td class="log_map"><?=$live["map"]?></td>
                                <td class="log_name"><a href="/view/<?=$live["log_ident"]?>"><?=$live["log_name"]?></a></td>

                            </tr>
                        </table>
                    </div>

                    <?php
                    }
                }
            }

        ?>
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
    
</body>

</html>

<?php
    pg_close($ll_db)
?>
