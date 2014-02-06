<?php

    function big_int_to_steamid($cid) {
        //converts a community id to a steamid
        $cid = (int)$cid - 76561197960265728;
        $cid_half = $cid / 2;

        if ($cid % 2) //if there's a remainder, auth server is server 1, else it's server 0
        {
            $auth_server = 1;
            $sid_chunk = $cid_half - 0.5;
        }
        else
        {
            $auth_server = 0;
            $sid_chunk = $cid_half; //last part of the steam id (i.e 1234567)
        }
        $steamid = sprintf("STEAM_0:%d:%d", $auth_server, $sid_chunk);
        return $steamid;
    }

    function player_classes($class_string)
    {
        //Gets passed a string of player classes. Must return a string of imgs wrt to the classes
        //class string: scout,soldier,demoman,medic,sniper

        $imgstring = " ";

        $split_class = explode(",", $class_string);

        foreach ($split_class as $idx => $class)
        {
            if ($class === "UNKNOWN")
            {
                $class = "noclass";
            }

            $imgstring .= '<img src="/images/classes/' . $class . '.png" style="max-width: 18px; max-height: 18px; height: auto; width: auto" alt="' . $class . '" title="' . strtoupper($class) . '"> ';
        }

        return $imgstring;
    }


    function steamid_to_bigint($steamid)
    {
        //from Seather @ https://forums.alliedmods.net/showpost.php?p=565979&postcount=16
        //Used in https://www.gamealphamoreecho.com/steamidconverter
    
        $iServer = "0";
        $iAuthID = "0";
        
        $szAuthID = $steamid;
        
        $szTmp = strtok($szAuthID, ":");
        
        while(($szTmp = strtok(":")) !== false)
        {
            $szTmp2 = strtok(":");
            if($szTmp2 !== false)
            {
                $iServer = $szTmp;
                $iAuthID = $szTmp2;
            }
        }

        if($iAuthID == "0")
            return "0";

        $i64friendID = bcmul($iAuthID, "2");

        //Friend ID's with even numbers are the 0 auth server.
        //Friend ID's with odd numbers are the 1 auth server.
        $i64friendID = bcadd($i64friendID, bcadd("76561197960265728", $iServer)); 
        
        return $i64friendID;
    }

    function get_player_team_class($team)
    {
        if ($team == "blue")
        {
            $team_class = "blue_player";
        }
        else if ($team == "red")
        {
            $team_class = "red_player";
        }
        else
        {
            $team_class = "no_team_player";
        }
        return $team_class;
    }

    function merge_stat_array($player_stats)
    {
        /*
        Take the player stat array and merge on steamid, adding all stat values together
        */

        $new_array = array();

        foreach ($player_stats as $index => $stat_data)
        {
            $curr_cid = $stat_data["steamid"];

            if (empty($new_array[$curr_cid]))
            {
                $new_array[$curr_cid] = array(); //create a new array under the player's steamid
            }

            $parray = &$new_array[$curr_cid];

            foreach ($stat_data as $key => $value)
            {
                //key is the database column names
                //value is the value of that column

                if ($key === "steamid")
                {
                    continue; //skip to the next key
                }

                //check for the stat key in the player's array
                if (empty($parray[$key]))
                {
                    $parray[$key] = $value;
                }
                else
                {
                    if ($key === "class")
                    {
                        $parray[$key] .= "," . $value;
                    }
                    else if ($key === "team")
                    {
                        //just update the name/team to whatever this is
                        if (!empty($value))
                        {
                            $parray[$key] = $value;
                        }
                    }
                    else
                    {
                        $parray[$key] += $value;
                    }
                }
            }

        }

        return $new_array;
    }

    function create_filtered_log_query($filter, $order, $limit)
    {
        require "../../conf/ll_config.php";

        $split_filter = explode(":", $filter);
        if (preg_match("/\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/", $split_filter[0]) && sizeof($split_filter) == 2)
        {
            //we have an ip:port search
            $escaped_address = pg_escape_string($split_filter[0]);
            $escaped_port = pg_escape_string($split_filter[1]);
            
            $query =   "SELECT DISTINCT HOST(server_ip) as server_ip, server_port, numeric_id, log_name, map, tstamp 
                        FROM {$ll_config["tables"]["log_index"]} 
                        WHERE (
                                TEXT(server_ip) = '{$escaped_address}' 
                                AND server_port = CAST('{$escaped_port}' AS INT)
                            )
                            AND live='false'
                        {$order}
                        {$limit}";

            $count_query = "SELECT COUNT(DISTINCT numeric_id) as total
                            FROM {$ll_config["tables"]["log_index"]} 
                            WHERE (
                                    TEXT(server_ip) = '{$escaped_address}' 
                                    AND server_port = CAST('{$escaped_port}' AS INT)
                                ) 
                                AND live='false'";
        }
        else if (preg_match("/^STEAM_(\d):(\d):(\d+)/", $filter))
        {
            //steam id match
            $cid = steamid_to_bigint($filter);

            $escaped_cid = pg_escape_string($cid);

            $query =   "SELECT DISTINCT HOST(server_ip) as server_ip, server_port, numeric_id, log_name, map, live, tstamp 
                        FROM {$ll_config["tables"]["log_index"]}
                        JOIN {$ll_config["tables"]["player_details"]} ON {$ll_config["tables"]["player_details"]}.log_ident = {$ll_config["tables"]["log_index"]}.log_ident 
                        WHERE steamid = '{$escaped_cid}' AND live='false'
                        {$order}
                        {$limit}";

            $count_query = "SELECT COUNT(DISTINCT numeric_id) as total
                        FROM {$ll_config["tables"]["log_index"]}
                        JOIN {$ll_config["tables"]["player_details"]} ON {$ll_config["tables"]["player_details"]}.log_ident = {$ll_config["tables"]["log_index"]}.log_ident 
                        WHERE steamid = '{$escaped_cid}' AND live='false'";
        }
        else
        {
            $escaped_filter = pg_escape_string($filter);

            $query =   "SELECT DISTINCT HOST(server_ip) as server_ip, server_port, numeric_id, log_name, map, tstamp 
                        FROM {$ll_config["tables"]["log_index"]} 
                        JOIN {$ll_config["tables"]["player_details"]} ON {$ll_config["tables"]["player_details"]}.log_ident = {$ll_config["tables"]["log_index"]}.log_ident
                        WHERE (
                                TEXT(server_ip) ~* '{$escaped_filter}' 
                                OR log_name ~* '{$escaped_filter}' 
                                OR map ~* '{$escaped_filter}' 
                                OR tstamp ~* '{$escaped_filter}'
                                OR name ~* '{$escaped_filter}'
                            )
                            AND live='false'
                        {$order}
                        {$limit}";

            $count_query = "SELECT COUNT(DISTINCT numeric_id) as total
                            FROM {$ll_config["tables"]["log_index"]} 
                            JOIN {$ll_config["tables"]["player_details"]} ON {$ll_config["tables"]["player_details"]}.log_ident = {$ll_config["tables"]["log_index"]}.log_ident
                            WHERE (
                                    TEXT(server_ip) ~* '{$escaped_filter}' 
                                    OR log_name ~* '{$escaped_filter}' 
                                    OR map ~* '{$escaped_filter}' 
                                    OR tstamp ~* '{$escaped_filter}'
                                    OR name ~* '{$escaped_filter}'
                                )
                                AND live='false'";
        }

        return array(0 => $query,
                     1 => $count_query
                    );
    }

    function fetch_name_array($name_res)
    {
        /* turns a pgsql result object with player names into an associative array wrt to cids */

        $name_array = array();

        while ($row = pg_fetch_array($name_res, NULL, PGSQL_ASSOC))
        {
            $narray = array();

            foreach ($row as $column => $value)
            {
                if ($column !== "steamid")
                    $narray[$column] = $value;
                
            }

            $name_array[$row["steamid"]] = $narray;
        }

        return $name_array;
    }

    function get_community_url($cid)
    {
        return '//steamcommunity.com/profiles/' . $cid;
    }

    function strip_string($str)
    {
        return htmlentities($str, ENT_QUOTES, "UTF-8");
    }

    function get_demo_url($basepath, $hash, $hashkey, $name)
    {
        //$ll_config["ozfortress"]["basepath"] . hash_hmac($ll_config["ozfortress"]["hashtype"], strtolower($log_details["log_name"]), $ll_config["ozfortress"]["hashkey"])
        return $basepath . hash_hmac($hash, strtolower($name), $hashkey);
    }
?>

