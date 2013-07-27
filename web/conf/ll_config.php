<?php
    $ll_config["websock"]["server_ip"] = "192.168.35.128"; //ip the websocket server is listening on
    $ll_config["websock"]["server_port"] = 61224; //port ^^^^^^^^^^^^^^^^^^^^^^^^^^

    $ll_config["display"]["index_num_past"] = 15; //number of past logs to display on index page
    $ll_config["display"]["archive_num"] = 25; //max number of logs to display per 'page' in archive paged table
    $ll_config["display"]["player_num_past"] = 20; //number of logs to display per 'page' in a paged table

    $ll_config["steam_api"]["key"] = "7CD8EC56801BD2F23A1A4184A1348ADD";

    $ll_config["ozfortress"]["basepath"] = "//heavy.ozfortress.com/demos/pub/";
    $ll_config["ozfortress"]["active"] = false;
    $ll_config["ozfortress"]["hashkey"] = "";
    $ll_config["ozfortress"]["hashtype"] = "sha1";

    $ll_config["tables"]["log_index"] = "livelogs_log_index";
    $ll_config["tables"]["player_stats"] = "livelogs_player_stats";
    $ll_config["tables"]["game_chat"] = "livelogs_game_chat";
    $ll_config["tables"]["player_details"] = "livelogs_player_details";
    $ll_config["tables"]["log_events"] = "livelogs_game_events";
?>

