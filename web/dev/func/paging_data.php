<?php
    /*
    This script gets database data and returns it in a format that DataTables can understand,
    which is required for paging that does not involve loading thousands of rows at the same time
    */

    require "../../conf/ll_database.php";

    $db_columns = array("server_ip", "server_port", "map", "log_name", "tstamp");

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
        $order = "ORDER BY numeric_id DESC, ";
        for ($i = 0; $i < intval($_GET['iSortingCols']); $i++)
        {
            if ($_GET['bSortable_'.intval($_GET['iSortCol_'.$i])] === "true")
            {
                $order .=  $db_columns[intval($_GET['iSortCol_'.$i])] . " " . ($_GET['sSortDir_'.$i] === asc ? 'ASC' : 'DESC') . ", ";
            }
        }

        $order = substr_replace($order, "", -2); //strip trailing ','

        if ($order == "ORDER BY") //if nothing was actually added to the order by
            $order = "";
    }

    //Filtering - filter by community id obviously, but also filter by others if search is enabled
    $filter = "WHERE steamid = '{$_GET['cid']}";
    
    /*if (isset($_GET['sSearch']) && $_GET['sSearch'] != "")
    {
        $filter .= " AND (";
        for ($i = 0; $i < count($db_columns); $i++)
        {
            if (isset($_GET['bSearchable_'.$i]) && $_GET['bSearchable_'.$i] === "true")
            {
                $filter .= " " . $db_columns[$i] . "~* " . pg_escape_string($_GET['sSearch']) . " OR ";
            }
        }


    }*/


    //THE QUERIES----------------

    $log_query = "SELECT DISTINCT server_ip, server_port, numeric_id, log_name, map, live, tstamp
                FROM livelogs_servers
                JOIN livelogs_player_stats ON livelogs_servers.log_ident = livelogs_player_stats.log_ident
                {$filter} 
                {$order} 
                {$limit}";

    $log_result = pg_query($ll_db);
    //length of results
    $num_logs_found = pg_num_rows($log_result);


    //total length of data set
    if ($num_logs_found > 0)
    {
        $total_logs_query = "SELECT COUNT(DISTINCT log_ident) as total
                            FROM livelogs_player_stats
                            {$filter}";

        $total_logs_result = pg_query($ll_db, $total_logs_query);
        if ($total_logs_result && pg_num_rows($total_logs_result) > 0)
        {
            $total_logs_array = pg_fetch_array($total_logs_result, NULL, PGSQL_ASSOC);
            $total_player_logs = $total_logs_array["total"];
        }
        else
            $total_player_logs = 0;
    }
    else
        $total_player_logs = 0;


    //NOW WE SEND THIS SHIT!
    $output = array(
        "sEcho" => intval($_GET['sEcho']), //a challenge ID
        "iTotalRecords" => $total_player_logs, //total logs matching
        "iTotalDisplayRecords" => $num_logs_found, //logs matching limit
        "aaData" => array()
    );


    /* populate the return array, and encode it to json */

    while ($row = pg_fetch_array($log_result))
    {
        $odata = array();
        

        $output['aaData'][] = $odata;
    }

    pg_close($ll_db);
?>
