<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <title>Livelogs DEV - INDEX</title>
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
    
        $live_query = "SELECT server_ip, server_port, log_ident, log_name, map FROM livelogs_servers WHERE live='true' ORDER BY numeric_id DESC";
        $live_res = pg_query($ll_db, $live_query);
    
        $past_query = "SELECT server_ip, server_port, log_ident, log_name, map FROM livelogs_servers WHERE live='false' ORDER BY numeric_id DESC LIMIT {$num_past}";
        $past_res = pg_query($ll_db, $past_query);
    ?>

</head>
<body class="ll_body">
    <div class="navbar navbar-inverse navbar-fixed-top">
        <div class="navbar-inner">
            <div class="livelogs_nav_container">
                <ul class="nav">
                    <li class="active">
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
        <div class="index_welcome">
            <p>Welcome to Livelogs! Below you will find a list of logs that are currently live (if any), and a list of past logs that you may view.</p>
        </div>
        <div>
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
                            <td class="server_ip"><?=long2ip($live["server_ip"])?></td>
                            <td class="server_port"><?=$live["server_port"]?></td>
                            <td class="log_map"><?=$live["map"]?></td>
                            <td class="log_name"><a href="/view/<?=$live["log_ident"]?>"><?=$live["log_name"]?></a></td>
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
                        $log_split = explode("_", $past["log_ident"]); //3232244481_27015_1356076576
                        
                    ?>
                        
                        <tr>
                            <td class="server_ip"><?=long2ip($past["server_ip"])?></td>
                            <td class="server_port"><?=$past["server_port"]?></td>
                            <td class="log_map"><?=$past["map"]?></td>
                            <td class="log_name"><a href="/view/<?=$past["log_ident"]?>"><?=$past["log_name"]?></a></td>
                            <td class="log_date"><?=date("d/m/Y   H:i:s", $log_split[2])?></td>
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
