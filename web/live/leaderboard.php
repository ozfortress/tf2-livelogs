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
            <p>This is the Livelogs leaderboard. It shows all players and their statistics, per class, within the last 30 days.</p>
        </div>
        <div class="leaderboard_filter_buttons btn-group" data-toggle="buttons-radio">
            <button id="filter_scout" class="btn" type="button">Scout</button>
            <button id="filter_soldier" class="btn" type="button">Soldier</button>
            <button id="filter_pyro" class="btn" type="button">Pyro</button>
            <button id="filter_demo" class="btn" type="button">Demo</button>
            <button id="filter_heavy" class="btn" type="button">Heavy</button>
            <button id="filter_medic" class="btn" type="button">Medic</button>
            <button id="filter_sniper" class="btn" type="button">Sniper</button>
            <button id="filter_engineer" class="btn" type="button">Engi</button>
            <button id="filter_spy" class="btn" type="button">Spy</button>
            <button id="filter_all" class="btn btn-info" type="button">ALL</button>
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
                            <abbr title="Points Captured">PC</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Headshots">HS</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Healing Done">H</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Overhealing Done">OH</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Damage Dealt">DMG</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Kills Per Death">KPD</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Damage Per Death">DPD</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Damage Per Kill">DPK</abbr>
                        </th>
                        <th class="stat_summary_col_title">
                            <abbr title="Number of games played">#G</abbr>
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
        lb_paging.init(<?=$ll_config["display"]["leaderboard_per_page"]?>);
    </script>

</body>
</html>

