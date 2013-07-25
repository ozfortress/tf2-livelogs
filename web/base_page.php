<!DOCTYPE html>
<html lang="en" xml:lang="en">
<head>
	<?php
        include 'static/header.html';

        require "../conf/ll_database.php";
        require "../conf/ll_config.php";
        require 'func/help_functions.php';

        if (!$ll_db)
            die();
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

    <?php include('static/logo.html'); ?>

    </div>
    <?php include('static/footer.html'); ?>

</body>
</html>

<?php
    pg_close($ll_db);
?>
