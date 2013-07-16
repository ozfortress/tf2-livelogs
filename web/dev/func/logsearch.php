<?php
    require "../../conf/ll_database.php";
    require "../../conf/ll_config.php";
    
    if (!$ll_db)
    {
        die("Unable to connect to database");
    }
    
    $table_cols = array("server_ip", "server_port", "map", "log_name", "tstamp");

    //Paging
    $limit = "";
    if (isset($_GET['iDisplayStart']) && $_GET['iDisplayLength'] != '-1')
    {
        $limit = "OFFSET " . intval($_GET['iDisplayStart']) . " LIMIT " . intval($_GET['iDisplayLength']);
    }

    //Data ordering
    $order = "ORDER BY numeric_id DESC";
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

    //search filtering and querying
    if (isset($_GET['sSearch']) && $_GET['sSearch'] != "")
    {
        $query_array = create_filtered_log_query($_GET['sSearch'], $order, $limit);
        $log_query = $query_array[0];
        $count_query = $query_array[1];
    }
    else
    {
        $log_query =   "SELECT HOST(server_ip) as server_ip, server_port, numeric_id, log_name, map, tstamp 
                        FROM livelogs_log_index 
                        WHERE live='false'
                        {$order}
                        {$limit}";

        $count_query = "SELECT COUNT(numeric_id) as total
                        FROM livelogs_log_index
                        WHERE live='false'";
    }

    /*
    ///////////// DOING STUFF WITH THE QUERY /////////////
    */

    file_put_contents("/tmp/past_paging_out.txt", $log_query + "\n");
    file_put_contents("/tmp/past_paging_out.txt", $order, FILE_APPEND);

    $log_result = pg_query($ll_db, $log_query);
    //length of results
    if ($log_result && ($num_logs_found = pg_num_rows($log_result)) > 0)
    {
        //total length of data set
        $total_logs_query = $count_query;

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
        "iTotalDisplayRecords" => $total_player_logs, //total logs found
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

    file_put_contents("/tmp/past_paging_out.txt", print_r($output, true), FILE_APPEND);
    
    pg_close($ll_db);
?>
