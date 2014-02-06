<?php
    require "../../conf/ll_database.php";

    if (!isset($_GET["key"]))
    {
        header("HTTP/1.1 403 Forbidden");
        echo("Forbidden");
        pg_close($ll_db);
        exit;
    }

    $escaped_key = pg_escape_string($_GET["key"]);
    $key_query = "SELECT EXISTS (SELECT 1 FROM livelogs_auth_keys WHERE user_key = '{$escaped_key}')";
    $key_res = pg_query($ll_db, $key_query);

    if (pg_num_rows($key_res) == 0)
    {
        header("HTTP/1.1 401 Unauthorized");
        echo("Unauthorized");
        pg_close($ll_db);
        exit;
    }
    

    if (isset($_GET["action"])) 
    {
        $action = $_GET["action"];
        $output = array();

        if ($action === "get_live")
        {
            $output["result"] = 1;
            $output["idents"] = array();

            $live_query = "SELECT log_ident FROM livelogs_log_index WHERE live='true'";
            $live_res = pg_query($ll_db, $live_query);

            if ($live_res)
            {
                while ($row = pg_fetch_array($live_res, NULL, PGSQL_ASSOC))
                {
                    $output["idents"][] = $row["log_ident"];
                }
            }
        }
        else if ($action === "get_stats")
        {
            $output["result"] = 1;
            $output["stats"] = array();

            $steamids = isset($_GET["steamids"]) ? $_GET["steamids"] : "";

            $sidarray = explode(",", $steamids);
            $escaped_ids = to_pg_list($sidarray);

            $filter = "WHERE steamid IN {$escaped_ids}";

            // support the selection of only stats from this API key
            if (isset($_GET["key_only"]))
            {
                $filter .= " AND log_ident IN (SELECT log_ident FROM livelogs_log_index WHERE api_key = '{$escaped_key}')";
            }

            $query = "SELECT steamid,
                         SUM(kills) as kills, SUM(deaths) as deaths, SUM(assists) as assists,
                         SUM(captures) as captures, SUM(headshots) as headshots,
                         SUM(healing_done) as healing_done, SUM(overhealing_done) as overhealing_done,
                         SUM(damage_dealt) as damage_dealt,
                         COUNT(log_ident) as numplayed
                      FROM livelogs_player_stats
                      {$filter}
                      GROUP BY steamid";

            $result = pg_query($ll_db, $query);

            if ($result)
            {
                while ($row = pg_fetch_array($result, NULL, PGSQL_ASSOC))
                {
                    $steamid = $row["steamid"];
                    unset($row["steamid"]);

                    $output["stats"][$steamid] = $row;
                }

            }
        }
        else
        {
            $output["result"] = 0;
        }

        echo json_encode($output);
    }
    else
    {
        header("HTTP/1.1 400 Bad Request");
    }

    pg_close($ll_db);

    function to_pg_list($array) {
        $array = (array) $array; // Type cast to array.
        $result = array();
        
        // Iterate through array.
        foreach ($array as $entry) 
        {
            $entry = str_replace('"', '\\"', $entry); // Escape double-quotes.
            $entry = pg_escape_string($entry); // Escape everything else.
            $result[] = '\'' . $entry . '\'';
            
        }

        return '(' . implode(',', $result) . ')'; // format
    }

?>
