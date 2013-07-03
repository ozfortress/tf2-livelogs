<?php
    require "../../conf/ll_database.php";
    require "../../conf/ll_config.php";
    
    if (!$ll_db)
    {
        die("Unable to connect to database");
    }

    if (!empty($ll_config["display"]["archive_num"]))
    {
        $num_logs = $ll_config["display"]["archive_num"];
    }
    else
    {
        $num_logs = 40;
    }
    
    $search_term = $_GET["term"];
    $result = "<tr>No results available</tr>";
    
    $split_search_term = explode(":", $search_term);
    if (sizeof($split_search_term) == 2)
    {
        //we most likely have an ip:port search
        $escaped_address = pg_escape_string(ip2long($split_search_term[0]));
        $escaped_port = pg_escape_string((int)$split_search_term[1]);
        
        $search_query = "SELECT server_ip, server_port, numeric_id, log_name, map, tstamp 
                        FROM livelogs_servers 
                        WHERE (server_ip = '{$escaped_address}' AND server_port = CAST('{$escaped_port}' AS INT)) AND live='false'
                        ORDER BY numeric_id DESC LIMIT {$num_logs}";
    }
    else
    {
        //did the user enter an IP?
        $longip = ip2long($search_term);
        
        if ($longip)
        {
            $escaped_search_term = pg_escape_string($longip);
        }
        else
        {
            $escaped_search_term = pg_escape_string($search_term);
        }
    
        $search_query = "SELECT server_ip, server_port, numeric_id, log_name, map, tstamp 
                        FROM livelogs_servers 
                        WHERE (server_ip ~* '{$escaped_search_term}' OR log_name ~* '{$escaped_search_term}' OR map ~* '{$escaped_search_term}' OR tstamp ~* '{$escaped_filter}') AND live='false'
                        ORDER BY numeric_id DESC LIMIT {$num_logs}";
    }
    
    $search_result = pg_query($ll_db, $search_query);
    
    if (!$search_result)
    {
        die("Unable to retrieve search results");
    }
    
    if (pg_num_rows($search_result) > 0)
    {
        $result = "";
        while ($log = pg_fetch_array($search_result, NULL, PGSQL_ASSOC))
        {
            $result .= '<tr>';
            $result .= '<td class="server_ip">' . long2ip($log["server_ip"]) . '</td>';
            $result .= '<td class="server_port">' . $log["server_port"] . '</td>';
            $result .= '<td class="log_map">' . $log["map"] . '</td>';
            $result .= '<td class="log_name"><a href="/view/' . $log["numeric_id"] . '">' . htmlentities($log["log_name"], ENT_QUOTES, "UTF-8") . '</a></td>';
            $result .= '<td class="log_date">' . $log["tstamp"] . '</td>';
        }
    }
    
    pg_close($ll_db);
    
    echo $result;
?>