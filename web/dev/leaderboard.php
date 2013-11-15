<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
	<?php
        include 'static/header.html';

        require "../conf/ll_config.php";
        require 'func/help_functions.php';
    ?>

    <title>Livelogs - Leaderboard</title>

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
                    <li>
                        <a href="/past">Archive</a>
                    </li>
                    <li class="active">
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
        <div class="text_blurb">
            <p>This is the Livelogs leaderboard. It shows the players with the highest Livelogs Rating (LLR) per class within the last 30 days.</p>
        </div>
        <div class="leaderboard_class_filter">
            <button class="btn" type="button">Scout</button>
            <button class="btn" type="button">Soldier</button>
            <button class="btn" type="button">Pyro</button>
            <button class="btn" type="button">Demo</button>
            <button class="btn" type="button">Heavy</button>
            <button class="btn" type="button">Medic</button>
            <button class="btn" type="button">Sniper</button>
            <button class="btn" type="button">Engi</button>
            <button class="btn" type="button">Spy</button>
        </div>
    	<div class="stat_table_container">
	    	<table id="leaderboard" class="table table-bordered table-striped table-hover ll_table">
                <thead>
                     <tr class="stat_summary_title_bar">
                        <th class="stat_summary_col_title">
                            <abbr title="Player Class">Class</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Player Name">Name</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Kills">K</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Deaths">D</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Assists">A</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Damage Dealt">DMG</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Number of games played">#G</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Livelogs player rating">LLR</abbr>
                        </th>
                    </tr>
                </thead>
                <tbody>

                </tbody>
                <caption>Livelogs leaderboard</caption>
	    	</table>
	    </div>

    	<?php include('static/logo.html'); ?>

    </div>
    <?php include('static/footer.html'); ?>

    <script src="/js/leaderboard.js" type="text/javascript"></script>
    <script type="text/javascript">
        // pass the display length (i.e how many rows per 'page')
        ll_paging.init(<?=$ll_config["display"]["leaderboard_per_page"]?>);
    </script>

</body>
</html>

<?php
    pg_close($ll_db);
?>
