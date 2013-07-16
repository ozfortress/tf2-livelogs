<?php
    /*
    This script gets database data and returns it in a format that DataTables can understand,
    which is required for paging that does not involve loading thousands of rows at the same time
    */

    require "../../conf/ll_database.php";

    $table_cols = array("server_ip", "server_port", "map", "log_name", "tstamp");

    if (!isset($_GET["cid"]))
    {
        die("STEAMID NOT SPECIFIED");
    }
    else
    {
        $cid = intval($_GET["cid"]);
    }

    //Paging
    $limit = "";
    if (isset($_GET['iDisplayStart']) && $_GET['iDisplayLength'] != '-1')
    {
        $limit = "OFFSET " . intval($_GET['iDisplayStart']) . " LIMIT " . intval($_GET['iDisplayLength']);
    }

    //Data ordering
    $order = "ORDER BY numeric_id DESC, ";
    if (isset($_GET['iSortCol_0']))
    {
        $order = "ORDER BY ";
        for ($i = 0; $i < intval($_GET['iSortingCols']); $i++)
        {
            if ($_GET['bSortable_'.intval($_GET['iSortCol_'.$i])] === "true")
            {
                $order .=  $table_cols[intval($_GET['iSortCol_'.$i])] . " " . ($_GET['sSortDir_'.$i] === 'asc' ? "ASC" : "DESC") . ", ";
            }
        }

        $order = substr_replace($order, "", -2); //strip trailing ', '
    }

    //Filtering - filter by community id obviously, but also filter by others if search is enabled
    $filter = "WHERE steamid = '{$cid}'";
    
    /*if (isset($_GET['sSearch']) && $_GET['sSearch'] != "")
    {
        $filter .= " AND (";
        for ($i = 0; $i < count($table_cols); $i++)
        {
            if (isset($_GET['bSearchable_'.$i]) && $_GET['bSearchable_'.$i] === "true")
            {
                $filter .= " " . $table_cols[$i] . "~* " . pg_escape_string($_GET['sSearch']) . " OR ";
            }
        }


    }*/


    //THE QUERIES----------------

    $log_query = "SELECT HOST(server_ip) as server_ip, server_port, numeric_id, log_name, map, live, tstamp
                FROM livelogs_servers
                JOIN livelogs_player_details ON livelogs_servers.log_ident = livelogs_player_details.log_ident
                {$filter} 
                {$order} 
                {$limit}";

    file_put_contents("/tmp/paging_out.txt", $log_query + "\n");
    file_put_contents("/tmp/paging_out.txt", $order, FILE_APPEND);

    $log_result = pg_query($ll_db, $log_query);
    //length of results
    if ($log_result && ($num_logs_found = pg_num_rows($log_result)) > 0)
    {
        //total length of data set
        $total_logs_query = "SELECT COUNT(log_ident) as total
                            FROM livelogs_player_details
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
    {
        $num_logs_found = 0;
        $total_player_logs = 0;
    }


    //NOW WE SEND THIS SHIT!
    $output = array(
        "sEcho" => intval($_GET['sEcho']), //a challenge ID
        "iTotalRecords" => $num_logs_found, //logs matching limit
        "iTotalDisplayRecords" => $total_player_logs, //total logs
        "community_id" => $cid,
        "aaData" => array()
    );


    /* populate the return array, and encode it to json */

    while ($row = pg_fetch_array($log_result, NULL, PGSQL_ASSOC))
    {
        $odata = array();

        foreach ($table_cols as $index => $key)
        {
            if ($key == "log_name")
            {
                /* this data should contain a link to the log */
                $data = '<a href="/view/' . $row["numeric_id"] . '">' . htmlentities($row["log_name"], ENT_QUOTES, "UTF-8") . '</a>';
            }
            else
            {
                $data = $row[$key];
            }

            $odata[] = $data;
        }
        
        $output['aaData'][] = $odata;
    }

    echo json_encode($output); //echo out the json encoded shiz

    file_put_contents("/tmp/paging_out.txt", print_r($output, true), FILE_APPEND);

    pg_close($ll_db);
?>
