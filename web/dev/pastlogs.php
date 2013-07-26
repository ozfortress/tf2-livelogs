<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
    <title>Livelogs - Archive</title>

    <?php
        include 'static/header.html';
        require "../conf/ll_config.php";

        if (!empty($ll_config["display"]["archive_num"]))
        {
            $num_logs = $ll_config["display"]["archive_num"];
        }
        else
        {
            $num_logs = 40;
        }
        
        if (empty($_GET["filter"]))
            $filter = null;
        else
            $filter = str_replace("/", "", $_GET["filter"]);
    ?>

</head>
<body class="ll_body">
    <div class="navbar navbar-inverse navbar-fixed-top">
        <div class="navbar-inner">
            <div class="livelogs_nav_container">
                <img class="pull-left" src="/images/livelogs-beta.png">
                <ul class="nav">
                    <li>
                        <a href="/">Home</a>
                    </li>
                    <li class="active">
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
        <p>Welcome to the Livelogs Archive</p>
        <p>You may sort the logs in accordance with any of the columns, and you may use the search to filter the logs you wish to view. 
            Possible searches include Steam ID, server, name, map name, log name, date, server ip or port, etc
        </p>
        <div class="log_list_past_container">
            <!--<form class="form-search" action="javascript:void(0);" id="search_form">
                <input type="text" class="pastlogs_searchfield" placeholder="Search here" id="search_field" value="<?=$filter?>">
                <button type="submit" class="btn" id="search_submit">Search</button>
            </form>-->
            <table class="table table-bordered table-hover table-striped ll_table" id="past_logs">
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
                
                </tbody>
            </table>
        </div>

        <?php include('static/logo.html'); ?>
    </div>
    <?php include('static/footer.html'); ?>

    <script src="/js/logsearch.js" type="text/javascript"></script>
    <script type="text/javascript">
        log_search.init("<?=$filter?>", <?=$num_logs?>);
    </script>
</body>

</html>

<?php
    pg_close($ll_db)
?>
