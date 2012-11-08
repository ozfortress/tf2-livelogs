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
            
            $escaped_ident = pg_escape_string($_GET["ident"]);
            
            $log_detail_query = "SELECT log_name, server_ip, server_port, map, live FROM livelogs_servers WHERE log_ident = '{$escaped_ident}'";
            $log_detail_res = pg_query($ll_db, $log_detail_query);

            ////server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean
            $log_details = pg_fetch_array($log_detail_res, 0, PGSQL_BOTH);
            if (!$log_details["log_name"])
            {
                die("404");
            }
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
        <div class="stat_summary">
        
        </div>
        <div class="event_feed">
        
        </div>
    </div>
</body>
</html>

<?php
    pg_close($ll_db)
?>
