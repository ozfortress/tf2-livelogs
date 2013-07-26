<?php
	require "../../conf/ll_database.php";

	if (isset($_GET['action'])) 
	{
		$output = array();

		if ($_GET['action'] === "get_live")
		{
			$live_query = "SELECT log_ident FROM livelogs_log_index WHERE live='true'";
			$live_res = pg_query($ll_db, $live_query);

			if ($live_res)
			{
				$output["live"] = array();

				while ($row = pg_fetch_array($live_res, NULL, PGSQL_ASSOC))
				{
					$output["live"][] = $row["log_ident"];
				}
			}

			echo json_encode($output);
		}
	}

	pg_close($ll_db);
?>