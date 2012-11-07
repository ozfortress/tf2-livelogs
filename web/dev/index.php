<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html lang="en" xml:lang="en">
<head>
    <meta content="text/html; charset=utf-8" http-equiv="Content-Type">

    <title>Livelogs DEV</title>

    <!--<link href="/favicon.ico" rel="shortcut icon">-->


    <?php
        $ll_db = pg_connect("host=localhost dbname=livelogs user=livelogs password=hello");

        if (!$ll_db)
        {
            $dataBaseError = true;
        }

    ?>

</head>
<body>
    <div class="wrapper">
        <div class="header">
            <p>HI!</p>
        </div>

        <div class="live_now">
            <?php
                if ($dataBaseError)
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
                        <p>No logs are currently live</p>
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
                                        <td class="log_name"><a href="./live/<?=$live["log_ident"]?>"><?=$live["log_name"]?></a></td>

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
</body>

</html>

<?php

?>
