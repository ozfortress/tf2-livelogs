<?php

    $dbuser = "livelogs";
    $dbpass = "hello";
    $dbhost = "localhost";
    $dbname = "livelogs";


    $ll_db = pg_connect("host=$dbhost dbname=$dbname user=$dbuser password=$dbpass");


?>