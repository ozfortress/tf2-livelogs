<?php
    /*
    This script gets database data and returns it in a format that DataTables can understand,
    which is required for paging that does not involve loading thousands of rows at the same time
    */

    require "../../conf/ll_database.php";

    $db_columns = array("numeric_id", "server_ip", "server_port", "map", "log_name", "tstamp");

    //Paging
    $limit = "":
    if (isset($_GET['iDisplayStart']) && $_GET['iDisplayLength'] != '-1')
    {
        $limit = "OFFSET " . intval($_GET['iDisplayStart']) . " LIMIT " . intval($_GET['iDisplayLength']);
    }

    //Data ordering
    $order = "";
    if (isset($_GET['iSortCol_0']))
    {
        $order = "ORDER BY ";
        
    }
?>