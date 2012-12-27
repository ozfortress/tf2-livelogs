<?php
    require "../../conf/ll_database.php";
    
    if (!$ll_db)
    {
        die("Unable to connect to database");
    }
    
    $search_term = $_GET["term"];
    $result = "No results available";
    
    $split_search_term = explode(":", $search_term);
    if (sizeof($split_search_term) == 2)
    {
        //we most likely have an ip:port search
        $escaped_address = pg_escape_string(ip2long($split_search_term[0]));
        $escaped_port = pg_escape_string((int)$split_search_term[1]);
        
        $search_query = "SELECT server_ip, server_port, log_ident, log_name, map 
                        FROM livelogs_servers 
                        WHERE (server_ip = '{$escaped_address}' AND server_port = CAST('{$escaped_port}' AS INT)) AND live='false'
                        ORDER BY numeric_id DESC LIMIT 40";
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
    
        $search_query = "SELECT server_ip, server_port, log_ident, log_name, map 
                        FROM livelogs_servers 
                        WHERE (server_ip ~* '{$escaped_search_term}' OR log_name ~* '{$escaped_search_term}' OR map ~* '{$escaped_search_term}') AND live='false'
                        ORDER BY numeric_id DESC LIMIT 40";
    }
    
    $search_result = pg_query($ll_db, $search_query);
    
    if (!$search_result)
    {
        die("Unable to retrieve search results");
    }
    
    if (pg_num_rows($search_result) > 0) //we have results, so we can assume our query was just the generic one
    {
        $result = "";
        while ($log = pg_fetch_array($search_result, NULL, PGSQL_ASSOC))
        {
            $log_split = explode("_", $log["log_ident"]);
        
            $result .= '<tr>';
            $result .= '<td class="server_ip">' . long2ip($log["server_ip"]) . '</td>';
            $result .= '<td class="server_port">' . $log["server_port"] . '</td>';
            $result .= '<td class="log_map">' . $log["map"] . '</td>';
            $result .= '<td class="log_name"><a href="/view/' . $log["log_ident"] . '">' . $log["log_name"] . '</a></td>';
            $result .= '<td class="log_date">' . date("d/m/Y H:i:s", $log_split[2]) . '</td>';
        }
    }
    else //what if the user entered a date? or a year? TODO: deal with this. there is currently no method of doing so, as dates are not indexed
    {
        echo $result;
    }
    
    pg_close($ll_db);
    
    echo $result;
?>