<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <title>Livelogs - Home</title>
    <?php
        include 'static/header.html';
        require "../conf/ll_database.php";
        require "../conf/ll_config.php";
        
        if (!$ll_db)
        {
            die("Unable to connect to database");
        }

        if (!empty($ll_config["display"]["index_num_past"]))
        {
            $num_past = $ll_config["display"]["index_num_past"];
        }
        else
        {
            $num_past = 15;
        }
    
        $live_query =  "SELECT HOST(server_ip) as server_ip, server_port, numeric_id, log_name, map 
                        FROM {$ll_config["tables"]["log_index"]}
                        WHERE live='true' 
                        ORDER BY numeric_id DESC";

        $live_res = pg_query($ll_db, $live_query);

    
        $past_query =  "SELECT HOST(server_ip) as server_ip, server_port, numeric_id, log_name, map, tstamp 
                        FROM {$ll_config["tables"]["log_index"]}
                        WHERE live='false' 
                        ORDER BY numeric_id DESC LIMIT {$num_past}";

        $past_res = pg_query($ll_db, $past_query);
    ?>

</head>
<body class="ll_body">
    <div class="navbar navbar-inverse navbar-fixed-top">
        <div class="navbar-inner">
            <div class="livelogs_nav_container">
                <img class="pull-left" src="/images/livelogs-beta.png">
                <ul class="nav">
                    <li class="active">
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
        <div class="page-header">
            <h3 align="center">Welcome to Livelogs!</h3>
        </div>
        <div class="text_blurb">
            <p align="center">Below you can find live logs (if any are running) that you may view, or a list of past recent past logs. 
                <br>Clicking 'See more' will allow you to view the log archive, which contains all logs recorded
            </p>
        </div>

        <div align="center">
            <?php
            if (!$live_res)
            {
            ?>
            
            <p class="text-error">Unable to retrieve live status</p>
            <?php
            }
            else if (pg_num_rows($live_res) > 0)
            {
            ?>
            
            <div class="log_list_container">
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
                        </tr>
                    </thead>
                    <tbody>
                    <?php
                    while ($live = pg_fetch_array($live_res, NULL, PGSQL_ASSOC))
                    {
                    //server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean
                    ?>
                       
                        <tr>
                            <td class="server_ip"><?=$live["server_ip"]?></td>
                            <td class="server_port"><?=$live["server_port"]?></td>
                            <td class="log_map"><?=$live["map"]?></td>
                            <td class="log_name"><a href="/view/<?=$live["numeric_id"]?>"><?=htmlentities($live["log_name"], ENT_QUOTES, "UTF-8")?></a></td>
                        </tr>
                    <?php
                    }
                    ?>
                    
                    </tbody>
                    <caption>Live</caption>
                </table>
            </div>
        <?php
            }

        ?>

            <div class="log_list_container">
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
                    <tbody>
                <?php
                    while ($past = pg_fetch_array($past_res, NULL, PGSQL_ASSOC))
                    {
                        //server_ip varchar(32) NOT NULL, server_port integer NOT NULL, log_ident varchar(64) PRIMARY KEY, map varchar(64) NOT NULL, log_name text, live boolean
                    ?>
                        
                        <tr>
                            <td class="server_ip"><?=$past["server_ip"]?></td>
                            <td class="server_port"><?=$past["server_port"]?></td>
                            <td class="log_map"><?=$past["map"]?></td>
                            <td class="log_name"><a href="/view/<?=$past["numeric_id"]?>"><?=htmlentities($past["log_name"], ENT_QUOTES, "UTF-8")?></a></td>
                            <td class="log_date"><?=$past["tstamp"]?></td>
                        </tr>
                    <?php
                    }
                    ?>
                    
                    </tbody>
                    <caption>Past <?=$num_past?> Logs (<a href="/past">See more</a>)</caption>
                </table>
                <p align="right"><a href="/past">See more</a></p>
            <?php
                }
            ?>
            
            </div>
            <div class="uploaded_logs">
            
            </div>
        </div>
        <?php include('static/logo.html'); ?>

    </div>
    <?php include('static/footer.html'); ?>

</body>

</html>

<?php
    pg_close($ll_db)
?>
