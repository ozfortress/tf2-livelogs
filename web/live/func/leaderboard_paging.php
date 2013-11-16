<?php
    /*
    This script gets database data and returns it in a format that DataTables can understand,
    which is required for paging that does not involve loading thousands of rows at the same time

    NOTE: intval() takes care of invalid strings passed as params (i.e sql injections)
    */

    require "../../conf/ll_database.php";
    require "../../conf/ll_config.php";
    require "help_functions.php";

    if (!$ll_db)
        die("");

    // the column order displayed in the table
    $table_cols = array("class", "name", "kills", "deaths", "assists", "captures", "headshots", "damage_dealt", "kpd", "dpd", "dpk", "numplayed");

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
    
    // if we have a search filter, it's by class
    if (isset($_GET['sSearch']) && $_GET['sSearch'] != "")
    {
        $filter = "WHERE class = '" . pg_escape_string($_GET['sSearch']) . "' AND steamid != 0";
    }


    //THE QUERIES----------------

    /* 
    Scoring algorithm: 
    */
    $query = "SELECT class, steamid,
                     SUM(kills) as kills, SUM(deaths) as deaths, SUM(assists) as assists, 
                     SUM(captures) as captures, SUM(headshots) as headshots, SUM(damage_dealt) as damage_dealt,
                     COUNT(log_ident) as numplayed
              FROM {$ll_config["views"]["month_stats"]}
              {$filter}
              GROUP BY class, steamid
              {$order}
              {$limit}";

    $namequery = "SELECT DISTINCT steamid, name
                  FROM {$ll_config["tables"]["player_details"]}
                    JOIN {$ll_config["views"]["month_idents"]} 
                    ON {$ll_config["tables"]["player_details"]}.log_ident = {$ll_config["views"]["month_idents"]}.log_ident";

    $result = pg_query($ll_db, $query);

    $nameresult = pg_query($ll_db, $namequery);
    $name_array = fetch_name_array($nameresult);
    
    //length of results
    if ($result && ($num_rows_found = pg_num_rows($result)) > 0)
    {
        //total length of data set
        $total_rows_query = "SELECT class, steamid 
                             FROM {$ll_config["views"]["month_stats"]} 
                             {$filter}
                             GROUP BY class, steamid;";

        $total_rows_result = pg_query($ll_db, $total_rows_query);
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
                $data = '<a href="/player/' . $cid . '">' . strip_string($name_array[$cid]["name"]) . '</a>';
            }
            else if ($key === "kpd")
            {
                $data = round($row["kills"] / ($row["deaths"] ? $row["deaths"] : 1), 2);
            }
            else if ($key === "dpd")
            {
                $data = round($row["damage_dealt"] / ($row["deaths"] ? $row["deaths"] : 1), 2);
            }
            else if ($key === "dpk")
            {
                $data = round($row["damage_dealt"] / ($row["kills"] ? $row["kills"] : 1), 2);
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
