<?php
    /*
    This script gets database data and returns it in a format that DataTables can understand,
    which is required for paging that does not involve loading thousands of rows at the same time
    */

    require "../../conf/ll_database.php";
    require "../../conf/ll_config.php";
    require "help_functions.php";

    if (!$ll_db)
        die("");

    // the column order displayed in the table
    $table_cols = array("class", "name", "kills", "deaths", "assists", "damage_dealt", "score");

    //Paging
    $limit = "";
    if (isset($_GET['iDisplayStart']) && $_GET['iDisplayLength'] != '-1')
    {
        $limit = "OFFSET " . intval($_GET['iDisplayStart']) . " LIMIT " . intval($_GET['iDisplayLength']);
    }

    //Data ordering
    $order = "ORDER BY score DESC, ";
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
    }
    $order = substr_replace($order, "", -2); //strip trailing ', '

    //filter out unknown classes
    $filter = "WHERE class != 'UNKNOWN' AND steamid != 0";
    
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
    $query = "SELECT class, steamid, SUM(kills+assists+captures)/COUNT(log_ident) as score, SUM(kills) as kills, 
                     SUM(deaths) as deaths, SUM(assists) as assists, SUM(damage_dealt) as damage_dealt 
              FROM {$ll_config["views"]["month_stats"]}
              GROUP BY class, steamid 
              {$filter}
              {$order}
              {$limit}";

    $namequery = "SELECT DISTINCT steamid, name
                  FROM {$ll_config["tables"]["player_details"]}
                    JOIN {$ll_config["views"]["month_idents"]} 
                    ON {$ll_config["tables"]["player_details"]}.log_ident = {$ll_config["views"]["month_idents"]}.log_ident";

    $result = pg_query($ll_db, $log_query);

    $nameresult = pg_query($ll_db, $namequery);
    $name_array = fetch_name_array($nameresult);
    
    //length of results
    if ($result && ($num_rows_found = pg_num_rows($result)) > 0)
    {
        //total length of data set
        $total_rows_query = "SELECT class, steamid 
                             FROM view_past_month_stats 
                             {$filter}
                             GROUP BY class, steamid;";

        $total_rows_result = pg_query($ll_db, $total_logs_query);
        if ($total_rows_result)
        {
            $total_rows = pg_num_rows($total_rows_result);
        }
        else
            $total_rows = 0;
    }
    else
    {
        $num_rows_found = 0;
        $total_rows = 0;
    }

    //NOW WE SEND THIS SHIT!
    $output = array(
        "sEcho" => intval($_GET['sEcho']), //a challenge ID
        "iTotalRecords" => $num_rows_found, //rows matching search & limit
        "iTotalDisplayRecords" => $total_rows, //total rows
        "aaData" => array()
    );


    /* populate the return array, and encode it to json */

    while ($row = pg_fetch_array($result, NULL, PGSQL_ASSOC))
    {
        $odata = array();

        $cid = $row["steamid"];

        foreach ($table_cols as $index => $key)
        {
            if ($key === "class")
            {
                /* this should be an image url */
                $data = player_classes($row[$key]);
            }
            else if ($key === "name")
            {
                // get the name from the name array based on the steamid (cid), but make it a link to the cid
                $data = '<a href="' . get_community_url($cid) . '">' . strip_string($name_array[$cid]["name"]) . '</a>';
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

    //close the db connection
    pg_close($ll_db);
?>
