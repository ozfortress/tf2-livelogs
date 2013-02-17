/*
    Credit to Carbon for basic structure of initiating actions on mp_tournament starts and ends
    To Jannik 'Peace-Maker' Hartung @ http://www.wcfan.de/ for basis of SourceTV2D
    To Cinq, Annuit Coeptis and Jean-Denis Caron for additional statistic logging such as damage done, heals, items and pausing/unpausing
*/

/** WEBTV SEND CODES
 * Control chars:
 * A: SourceTV2D spectator amount changed
 * B: Bomb action, see BOMB_ defines
 * C: Player connected
 * D: Player disconnected
 * E: Round ended
 * F: FLAG ACTION - intel pickup, capture, defend, drop
 * G: Player changed class
 * H: Player was hurt
 * I: Initial child socket connect. Sends game and map, and current scores
 * J:
 * K: Player died
 * L:
 * M: Map changed
 * N: Player changed his name
 * O: Player position update
 * P:
 * Q: 
 * R: Round start
 * S: Player spawned
 * T: Player changed team
 * U: Player used ubercharge
 * V: ConVar changed
 * W:
 * X: Chat message
 * Y: 
 * Z: SourceTV2D spectator chat
 */


#pragma semicolon 1 //must use semicolon to end lines

#include <sourcemod>
#include <socket>
#include <sdktools>

#include <livelogs>

#undef REQUIRE_PLUGIN

#tryinclude <websocket>

#if defined _websocket_included
#include <tf2_stocks>
#endif                           

public Plugin:myinfo =
{
    #if defined _websocket_included
	name = "Livelogs (SourceTV2D Capable)",
    #else
    name = "Livelogs (SourceTV2D Disabled)",
    #endif
	author = "Prithu \"bladez\" Parker",
	description = "Server-side plugin for the livelogs system. Sends logging request to the livelogs daemon and instigates logging procedures",
	version = "0.4.0",
	url = "http://livelogs.ozfortress.com"
};



//------------------------------------------------------------------------------
// Variables
//------------------------------------------------------------------------------

new bool:tournament_state[2] = { false, false }; //Holds ready state for both teams
new bool:live_on_restart = false;
new bool:is_logging = false;
new bool:late_loaded;
new bool:livelogs_bitmask_cache[64];
new bool:create_new_log_file = false;

new String:server_ip[64];
new String:listener_address[128];
new String:log_unique_ident[64];
new String:client_index_cache[MAXPLAYERS+1][64];

new log_additional_stats;
new server_port;

//Handles for convars
new Handle:livelogs_daemon_address = INVALID_HANDLE; //ip/dns of livelogs daemon
new Handle:livelogs_daemon_port = INVALID_HANDLE; //port of livelogs daemon
new Handle:livelogs_daemon_api_key = INVALID_HANDLE; //the key that must be specified when communicating with the ll daemon
new Handle:livelogs_server_name = INVALID_HANDLE;
new Handle:livelogs_logging_level = INVALID_HANDLE;
new Handle:livelogs_ipgn_booking_name = INVALID_HANDLE;
new Handle:livelogs_new_log_file = INVALID_HANDLE;
new Handle:livelogs_enabled = INVALID_HANDLE;

//if websocket is included, let's define the websocket stuff!
#if defined _websocket_included
new webtv_round_time;
new livelogs_webtv_buffer_length = 0;

new bool:webtv_library_present = false;
new bool:webtv_enabled = true;

new Float:webtv_delay;

new WebsocketHandle:livelogs_webtv_listen_socket = INVALID_WEBSOCKET_HANDLE;
new Handle:livelogs_webtv_listen_port = INVALID_HANDLE;
new Handle:livelogs_webtv_children = INVALID_HANDLE;
new Handle:livelogs_webtv_children_ip = INVALID_HANDLE;
new Handle:livelogs_webtv_enabled = INVALID_HANDLE;
new Handle:livelogs_webtv_buffer_timer = INVALID_HANDLE; //timer to process the buffer every WEBTV_UPDATE_RATE seconds, only sends events that have time >= tv_delay
new Handle:livelogs_webtv_positions_timer = INVALID_HANDLE;
new Handle:livelogs_webtv_cleanup_timer = INVALID_HANDLE;
new Handle:livelogs_server_hostname = INVALID_HANDLE; //for caching the hostname cvar handle
new Handle:livelogs_server_tv_delay = INVALID_HANDLE; //for caching the tv_delay cvar handle

new String:livelogs_webtv_buffer[MAX_BUFFER_SIZE][4096]; //string array buffer, MUCH faster than dynamic arrays
#endif

//------------------------------------------------------------------------------
// Startup
//------------------------------------------------------------------------------

public APLRes:AskPluginLoad2(Handle:myself, bool:late, String:error[], err_max)
{
    late_loaded = late;
    return APLRes_Success;
}

public OnPluginStart()
{
    // Console command to test socket sending
    RegConsoleCmd("test_livelogs", Test_SockSend);

    // Tournament state change
    HookEvent("tournament_stateupdate", tournamentStateChangeEvent);

    // Game restarted (mp_restartgame, or when tournament countdown ends)
    HookEvent("teamplay_restart_round", gameRestartEvent);

    //game over events
    HookEvent("tf_game_over", gameOverEvent); //mp_windifference_limit
    HookEvent("teamplay_game_over", gameOverEvent); //mp_maxrounds, mp_timelimit, mp_winlimit

    // Hook into mp_tournament_restart
    AddCommandListener(tournamentRestartHook, "mp_tournament_restart");

    //Hook events for additional statistic display
    HookEvent("item_pickup", itemPickupEvent); //item is picked up
    HookEvent("player_hurt", playerHurtEvent); //player is hurt
    HookEvent("player_healed", playerHealEvent); //player receives healing, from dispenser or medic

    //Listen for chat commands
    RegConsoleCmd("sm_livelogs", urlCommandCallback, "Displays the livelogs log URL to the client");

    //Convars
    livelogs_daemon_address = CreateConVar("livelogs_address", "192.168.35.128", "IP or hostname of the livelogs daemon", FCVAR_PROTECTED);
    
    livelogs_daemon_port = CreateConVar("livelogs_port", "61222", "Port of the livelogs daemon", FCVAR_PROTECTED);
    
    livelogs_daemon_api_key = CreateConVar("livelogs_api_key", "123test", "API key for livelogs daemon", FCVAR_PROTECTED|FCVAR_DONTRECORD|FCVAR_UNLOGGED);

    livelogs_server_name = CreateConVar("livelogs_name", "default", "The name by which logs are identified on the website", FCVAR_PROTECTED);

    livelogs_logging_level = CreateConVar("livelogs_additional_logging", "15", "Set logging level. See FAQ for logging bitmask values",
                                            FCVAR_NOTIFY, true, 0.0, true, 64.0); //allows levels of logging via a bitmask

    livelogs_new_log_file = CreateConVar("livelogs_new_log_file", "0", "Whether to initiate console logging using 'log on'. Disable if you have another method of enabling logging", 
                                            FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_enabled = CreateConVar("livelogs_enabled", "1", "Enable or disable Livelogs", FCVAR_NOTIFY, true, 0.0, true, 1.0);

    HookConVarChange(livelogs_new_log_file, logFileToggleHook);
    HookConVarChange(livelogs_logging_level, loggingLevelChangeHook); //hook convar so we can change logging options on the fly

    //variables for later sending. we should get the IP via hostip, because sometimes people may not set "ip"
    new longip = GetConVarInt(FindConVar("hostip")), ip_quad[4];
    ip_quad[0] = (longip >> 24) & 0x000000FF;
    ip_quad[1] = (longip >> 16) & 0x000000FF;
    ip_quad[2] = (longip >> 8) & 0x000000FF;
    ip_quad[3] = (longip) & 0x000000FF;
    
    Format(server_ip, sizeof(server_ip), "%d.%d.%d.%d", ip_quad[0], ip_quad[1], ip_quad[2], ip_quad[3]);
    
    server_port = GetConVarInt(FindConVar("hostport"));

#if defined _websocket_included
    new String:default_web_port[12];
    Format(default_web_port, sizeof(default_web_port), "%d", server_port + 2);
    
    livelogs_webtv_listen_port = CreateConVar("livelogs_webtv_port", default_web_port, "The port to listen on for SourceTV 2D connections", FCVAR_PROTECTED);
    livelogs_webtv_enabled = CreateConVar("livelogs_enable_webtv", "1", "Toggle whether or not SourceTV2D will run",
                                    FCVAR_NOTIFY, true, 0.0, true, 1.0);


    livelogs_webtv_children = CreateArray();
    livelogs_webtv_children_ip = CreateArray(ByteCountToCells(33));

    livelogs_server_tv_delay = FindConVar("tv_delay"); //cache the tv_delay convar handle

    //add event hooks and shiz for websocket, self explanatory names and event hooks
    HookEvent("player_team", playerTeamChangeEvent);
    HookEvent("player_death", playerDeathEvent);
    HookEvent("player_spawn", playerSpawnEvent);
    HookEvent("player_changeclass", playerClassChangeEvent);
    HookEvent("player_chargedeployed", playerUberEvent);
    HookEvent("teamplay_flag_event", playerFlagEvent);
    HookEvent("teamplay_round_start", roundStartEvent);
    HookEvent("teamplay_round_win", roundEndEvent);
    
    HookConVarChange(livelogs_webtv_enabled, toggleWebTVHook); //hook the webtv enable cvar, so we can enable/disable on the fly
    HookConVarChange(livelogs_server_tv_delay, delayChangeHook); //hook tv_delay so we can adjust the delay dynamically
#endif

    if (late_loaded)
    {
        decl String:auth[64];
        for (new i = 1; i <= MaxClients; i++)
        {
            if (IsClientInGame(i) && IsClientAuthorized(i) && !IsFakeClient(i))
            {
                GetClientAuthString(i, auth, sizeof(auth));
                OnClientAuthorized(i, auth); //call to onclientauth, which will cache the auth for us
            }
        }
        
        getConVarValues(); //we need to get the value of convars that are already set if the plugin is loading late
    }
}


public OnAllPluginsLoaded()
{
    //check convar settings & update
    new cvar_val = GetConVarInt(livelogs_logging_level);
    log_additional_stats = cvar_val;

    if (livelogs_ipgn_booking_name == INVALID_HANDLE)
    {
        livelogs_ipgn_booking_name = ConVarExists("mr_ipgnbooker");
    }

    #if defined _websocket_included
    if (LibraryExists("websocket"))
    {
        webtv_library_present = true;
        if (DEBUG) { LogMessage("Websocket library present. Using SourceTV2D"); }
        
        cleanUpWebSocket();
    }
    else
        if (DEBUG) { LogMessage("Websocket library is not present. Not using SourceTV2D"); }
    #endif
}

public OnMapStart()
{
	clearVars();
    
#if defined _websocket_included
    livelogs_webtv_buffer_timer = INVALID_HANDLE;
    livelogs_webtv_positions_timer = INVALID_HANDLE;
    livelogs_webtv_cleanup_timer = INVALID_HANDLE;
#endif
}

#if defined _websocket_included
public OnLibraryAdded(const String:name[])
{
    //this forward is only fired if websocket is added
    if (StrEqual(name, "websocket"))
    {
        webtv_library_present = true;
        cleanUpWebSocket();
    }
}

public OnLibraryRemoved(const String:name[])
{
    //this forward is only fired if websocket is added
    if (StrEqual(name, "websocket"))
    {
        webtv_library_present = false;
        cleanUpWebSocket();
    }
}
#endif

//------------------------------------------------------------------------------
// Callbacks
//------------------------------------------------------------------------------

public OnClientAuthorized(client, const String:auth[])
{
    //cache the client's steam id, for performance in event hooks
    strcopy(client_index_cache[client], sizeof(client_index_cache[]), auth);
}

public OnClientDisconnect(client)
{
    strcopy(client_index_cache[client], sizeof(client_index_cache[]), "\0"); //clear client's steamid
    
    #if defined _websocket_included
    if (IsClientInGame(client))
    {
        decl String:buffer[12];
        Format(buffer, sizeof(buffer), "D%d", GetClientUserId(client));
        
        addToWebBuffer(buffer);
    }
    #endif
}

public Action:urlCommandCallback(client, args)
{
    //WE CAN IGNORE THE ARGS
    if (client == 0) 
    {
        PrintToServer("Log URL: http://livelogs.ozfortress.com/view/%s", log_unique_ident);
        return Plugin_Handled;
    }

    if (strlen(log_unique_ident) > 1)
    {
        //we have a log ident to print to the client

        PrintToChat(client, "Log URL: http://livelogs.ozfortress.com/view/%s", log_unique_ident);
    }
    else
    {
        PrintToChat(client, "No log URL is available");
    }

    return Plugin_Handled;
}

public logFileToggleHook(Handle:cvar, const String:oldval[], const String:newval[])
{
    create_new_log_file = GetConVarBool(cvar);

    if (create_new_log_file)
    {
        PrintToServer("Livelogs will enable logging using 'log on' on match start");
    }
    else
    {
        PrintToServer("Livelogs will not enable console log output on match start (no 'log on')");
    }
}

public loggingLevelChangeHook(Handle:cvar, const String:oldval[], const String:newval[])
{
    if (DEBUG) { LogMessage("Additional logging toggled. old: %s new: %s", oldval, newval); }
    
    log_additional_stats = GetConVarInt(cvar); //going to have multiple levels of logging

    if (log_additional_stats > 0) 
    {
        PrintToServer("Livelogs now outputting additional logging");
    }
    else
    {
        PrintToServer("Livelogs no longer outputting additional statistics");
    }

    //set all values in the bitmask cache to false
    for (new i = 0; i < sizeof(livelogs_bitmask_cache); i++)
    {
        livelogs_bitmask_cache[i] = false;
    }

}

public tournamentStateChangeEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    new client_team = GetClientTeam(GetEventInt(event, "userid")) - TEAM_OFFSET;
    new bool:r_state = GetEventBool(event, "readystate");

    new bool:is_name_change = GetEventBool(event, "namechange");
    if (!is_name_change)
    {
        tournament_state[client_team] = r_state;

        //we're ready to begin logging at round restart if both teams are ready
        if (tournament_state[RED] && tournament_state[BLUE])
        {
            live_on_restart = true;
        }
        else
        {
            live_on_restart = false;
        }
    }
}

public gameRestartEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    //if teams are ready, get log listener address
    if (live_on_restart)
    {
        if (create_new_log_file)
        {
            ServerCommand("log on"); //create new log file, enable console log output
        }

        if (GetConVarInt(livelogs_enabled))
        {
            requestListenerAddress();

            is_logging = true;
        }

        live_on_restart = false;
        tournament_state[RED] = false;
        tournament_state[BLUE] = false;
    }
}

public gameOverEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
	endLogging(); //stop the logging -- does this really need to be done? hmmm
}

public itemPickupEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    if (log_additional_stats && logOptionEnabled(BITMASK_ITEM_PICKUP))
    {
        decl String:player_name[MAX_NAME_LENGTH], String:auth_id[64], String:team[16], String:item[64];

        new userid = GetEventInt(event, "userid");
        new clientidx = GetClientOfUserId(userid);

        strcopy(auth_id, sizeof(auth_id), client_index_cache[clientidx]); //get the player ID from the cache if it's in there

        GetClientName(clientidx, player_name, sizeof(player_name));
        GetTeamName(GetClientTeam(clientidx), team, sizeof(team));
        GetEventString(event, "item", item, sizeof(item));

        LogToGame("\"%s<%d><%s><%s>\" picked up item \"%s\"",
                player_name,
                userid,
                auth_id,
                team,
                item
            );
    }
}

public playerHurtEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    if (log_additional_stats) {

        if (logOptionEnabled(BITMASK_DAMAGE_TAKEN) && logOptionEnabled(BITMASK_DAMAGE_DEALT))
        {
            new victimid = GetEventInt(event, "userid");
            new attackerid = GetEventInt(event, "attacker");

            if (victimid != attackerid && attackerid != 0)
            {
                decl String:victim_name[MAX_NAME_LENGTH], String:victim_auth_id[64], String:victim_team[16];
                decl String:player_name[MAX_NAME_LENGTH], String:auth_id[64], String:team[16];

                new attackeridx = GetClientOfUserId(attackerid);
                new victimidx = GetClientOfUserId(victimid);

                new damage = GetEventInt(event, "damageamount");

                strcopy(auth_id, sizeof(auth_id), client_index_cache[attackeridx]); //get the player ID from the cache if it's in there
                strcopy(victim_auth_id, sizeof(victim_auth_id), client_index_cache[victimidx]);

                GetClientName(attackeridx, player_name, sizeof(player_name));
                GetClientName(victimidx, victim_name, sizeof(victim_name));

                GetTeamName(GetClientTeam(attackeridx), team, sizeof(team));
                GetTeamName(GetClientTeam(victimidx), victim_team, sizeof(victim_team));

                LogToGame("\"%s<%d><%s><%s>\" triggered \"damage\" against \"%s<%d><%s><%s>\" (damage \"%d\")",
                        player_name,
                        attackerid,
                        auth_id,
                        team,
                        victim_name,
                        victimid,
                        victim_auth_id,
                        victim_team,
                        damage
                    );
            }
        }
        else if (logOptionEnabled(BITMASK_DAMAGE_TAKEN))
        {
            new victimid = GetEventInt(event, "userid");
            new attackerid = GetEventInt(event, "attacker");
            
            if (victimid != attackerid)
            {
                decl String:player_name[MAX_NAME_LENGTH], String:auth_id[64], String:team[16];

                new victimidx = GetClientOfUserId(victimid);
                new damage = GetEventInt(event, "damageamount");

                strcopy(auth_id, sizeof(auth_id), client_index_cache[victimidx]); //get the player ID from the cache if it's in there
            
                GetClientName(victimidx, player_name, sizeof(player_name));
                GetTeamName(GetClientTeam(victimidx), team, sizeof(team));

                LogToGame("\"%s<%d><%s><%s>\" triggered \"damage_taken\" (damage \"%d\")",
                        player_name,
                        victimid,
                        auth_id,
                        team,
                        damage
                    );
            }
        }
        else if (logOptionEnabled(BITMASK_DAMAGE_DEALT))
        {
            new victimid = GetEventInt(event, "userid");
            new attackerid = GetEventInt(event, "attacker");
            
            if (victimid != attackerid && attackerid != 0)
            {
                decl String:player_name[MAX_NAME_LENGTH], String:auth_id[64], String:team[16];
                new attackeridx = GetClientOfUserId(attackerid);

                new damage = GetEventInt(event, "damageamount");

                strcopy(auth_id, sizeof(auth_id), client_index_cache[attackeridx]);
                GetClientName(attackeridx, player_name, sizeof(player_name));
                GetTeamName(GetClientTeam(attackeridx), team, sizeof(team));

                LogToGame("\"%s<%d><%s><%s>\" triggered \"damage\" (damage \"%d\")",
                        player_name,
                        attackerid,
                        auth_id,
                        team,
                        damage
                    );
            }
        }
    }
}

public playerHealEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    if (log_additional_stats && logOptionEnabled(BITMASK_HEALING)) {
        decl String:healer_name[MAX_NAME_LENGTH], String:healer_auth[64], String:healer_team[16];
        decl String:patient_name[MAX_NAME_LENGTH], String:patient_auth[64], String:patient_team[16];

        new healerid = GetEventInt(event, "healer");
        new healer_idx = GetClientOfUserId(healerid);

        new patientid = GetEventInt(event, "patient");
        new patient_idx = GetClientOfUserId(patientid);

        strcopy(healer_auth, sizeof(healer_auth), client_index_cache[healer_idx]);
        strcopy(patient_auth, sizeof(patient_auth), client_index_cache[patient_idx]);
        
        GetClientName(healer_idx, healer_name, sizeof(healer_name));
        GetClientName(patient_idx, patient_name, sizeof(patient_name));

        GetTeamName(GetClientTeam(healer_idx), healer_team, sizeof(healer_team));
        GetTeamName(GetClientTeam(patient_idx), patient_team, sizeof(patient_team));

        new heal_amount = GetEventInt(event, "amount");

        LogToGame("\"%s<%d><%s><%s>\" triggered \"healed\" against \"%s<%d><%s><%s>\" (healing \"%d\")",
                healer_name,
                healerid,
                healer_auth,
                healer_team,
                patient_name,
                patientid,
                patient_auth,
                patient_team,
                heal_amount
            );
    }
}

public Action:tournamentRestartHook(client, const String:command[], arg)
{
    //mp_tournament_restart was used, we should end logging so a new log can be initiated for the next start
    if (is_logging)
    {
        endLogging();
    }
}

//------------------------------------------------------------------------------
// WEBSOCKET CALLBACKS (STV2D)
//------------------------------------------------------------------------------

#if defined _websocket_included

public toggleWebTVHook(Handle:cvar, const String:oldval[], const String:newval[])
{
    if (DEBUG) { LogMessage("webtv toggled"); }
    webtv_enabled = GetConVarBool(cvar);

    if (webtv_enabled) 
    {
        PrintToServer("SourceTV2D enabled");
    }
    else
    {
        PrintToServer("SourceTV2D disabled");

        cleanUpWebSocket();
    }
}

public delayChangeHook(Handle:cvar, const String:oldval[], const String:newval[])
{
    if (DEBUG) { LogMessage("delay changed. old: %s new: %s", oldval, newval); }
    
    webtv_delay = StringToFloat(newval);
}

public OnClientPutInServer(client)
{
    new num_web_clients = GetArraySize(livelogs_webtv_children);
    if (num_web_clients == 0)
        return;
        
    decl String:buffer[128];
    //CUSERID:IP:TEAM:ALIVE:FRAGS:DEATHS:HEALTH:BOMB:DEFUSER:NAME
    Format(buffer, sizeof(buffer), "C%d:%s:%d:0:x:x:100:0:0:%N", GetClientUserId(client), "0.0.0.0", GetClientTeam(client), client);
    
    sendToAllWebChildren(buffer);
}

public playerTeamChangeEvent(Handle: event, const String:name[], bool:dontBroadcast)
{
    new userid = GetEventInt(event, "userid");
    new team = GetEventInt(event, "team");
    if (team == 0)
        return;
        
    decl String:buffer[12];
    Format(buffer, sizeof(buffer), "T%d:%d", userid, team);
    
    addToWebBuffer(buffer);
}

public playerDeathEvent(Handle:event, const String:name[], bool:dontBroadcast)
{       
    new v_id = GetEventInt(event, "userid");
    new a_id = GetEventInt(event, "attacker");
    
    decl String:buffer[64];
    GetEventString(event, "weapon", buffer, sizeof(buffer));
    
    Format(buffer, sizeof(buffer), "K%d:%d:%s", v_id, a_id, buffer);
    
    addToWebBuffer(buffer);
}

public playerSpawnEvent(Handle:event, const String:name[], bool:dontBroadcast)
{       
    new userid = GetEventInt(event, "userid");
    new pclass = GetEventInt(event, "class");
    
    decl String:buffer[12];
    Format(buffer, sizeof(buffer), "S%d:%d", userid, pclass);
    
    addToWebBuffer(buffer);
}

public playerClassChangeEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    new userid = GetEventInt(event, "userid");
    new pclass = GetEventInt(event, "class");
    
    decl String:buffer[12];
    
    Format(buffer, sizeof(buffer), "G%d:%d", userid, pclass);
    
    addToWebBuffer(buffer);
}

public playerUberEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    new m_userid = GetEventInt(event, "userid"); //userid of medic
    new t_userid = GetEventInt(event, "targetid"); //userid of medic's target
    
    decl String:buffer[12];
    Format(buffer, sizeof(buffer), "U:%d:%d", m_userid, t_userid);
    
    addToWebBuffer(buffer);
}

public playerFlagEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    new userid = GetEventInt(event, "player");
    new etype = GetEventInt(event, "eventtype");
    
    decl String:buffer[12];
    Format(buffer, sizeof(buffer), "F:%d:%d", userid, etype);
    
    addToWebBuffer(buffer);
}

public roundStartEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
        
    webtv_round_time = GetTime();
    
    new bool:full_restart = GetEventBool(event, "full_reset"); //whether or not this is mp_restartgame or not
    
    decl String:buffer[64];
    Format(buffer, sizeof(buffer), "R%d:%d", webtv_round_time, full_restart);
    
    addToWebBuffer(buffer);
}

public roundEndEvent(Handle:event, const String:name[], bool:dontBroadcast)
{       
    webtv_round_time = -1;
    
    new winner = GetEventInt(event, "team");
    
    decl String:buffer[12];
    Format(buffer, sizeof(buffer), "E%d", winner);
    
    addToWebBuffer(buffer);
}

public nameChangeEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    new num_web_clients = GetArraySize(livelogs_webtv_children);
    if (num_web_clients == 0)
        return;
        
    new userid = GetEventInt(event, "userid");
    
    decl String:old_name[MAX_NAME_LENGTH];
    decl String:new_name[MAX_NAME_LENGTH];
    
    GetEventString(event, "newname", new_name, sizeof(new_name));
    GetEventString(event, "oldname", old_name, sizeof(old_name));
    
    if (StrEqual(old_name, new_name))
        return;
        
    decl String:buffer[MAX_NAME_LENGTH+12];
    Format(buffer, sizeof(buffer), "N%d:%s", userid, new_name);
    
    addToWebBuffer(buffer);
}

public Action:onWebSocketConnection(WebsocketHandle:listen_sock, WebsocketHandle:child_sock, const String:remoteIP[], remotePort, String:protocols[256])
{
    if (DEBUG) { LogMessage("Incoming connection from %s:%d", remoteIP, remotePort); }
    Websocket_HookChild(child_sock, onWebSocketChildReceive, onWebSocketChildDisconnect, onWebSocketChildError);
    Websocket_HookReadyStateChange(child_sock, onWebSocketReadyStateChange);
    
    PushArrayCell(livelogs_webtv_children, child_sock);
    PushArrayString(livelogs_webtv_children_ip, remoteIP);
    
    return Plugin_Continue;
}

public onWebSocketReadyStateChange(WebsocketHandle:sock, WebsocketReadyState:readystate)
{
    if (DEBUG) { LogMessage("r state change"); }

    new child_index = FindValueInArray(livelogs_webtv_children, sock);
    if (child_index == -1)
        return;
    
    if (readystate != State_Open)
        return;
        
    decl String:map[64], String:game[32], String:hostname[128];
    new String:buffer[196];

    GetCurrentMap(map, sizeof(map));
    GetGameFolderName(game, sizeof(game));
    
    if (livelogs_server_hostname == INVALID_HANDLE)
    {
        livelogs_server_hostname = FindConVar("hostname");
    }

    GetConVarString(livelogs_server_hostname, hostname, sizeof(hostname));
    
    new red_score = GetTeamScore(RED+TEAM_OFFSET);
    new blue_score = GetTeamScore(BLUE+TEAM_OFFSET);

    //IGAME:MAP:TEAM2NAME:TEAM3NAME:TEAM2SCORE:TEAM3SCORE:HOSTNAME
    FormatEx(buffer, sizeof(buffer), "I%s:%s:%s:%s:%d:%d:%s", game, map, "RED", "BLUE", red_score, blue_score, hostname);
    
    Websocket_Send(sock, SendType_Text, buffer);
    
    if (webtv_round_time != -1)
    {
        Format(buffer, sizeof(buffer), "R%d", webtv_round_time);
    }
    
    //populate with all players in the server
    for (new i = 1; i <= MaxClients; i++)
    {
        if (IsClientInGame(i) && !IsFakeClient(i))
        {
            //CUSERID:IP:TEAM:ALIVE:FRAGS:DEATHS:HEALTH:CLASS:INTEL:NAME
            Format(buffer, sizeof(buffer), "C%d:%s:%d:%d:%d:%d:%d:%d:%d:%N", GetClientUserId(i), "0.0.0.0", 
                    GetClientTeam(i), IsPlayerAlive(i), GetClientFrags(i), GetClientDeaths(i), 100, TF2_GetPlayerClass(i), 0, i);
                    
            Websocket_Send(sock, SendType_Text, buffer);
        }
    }
    
    if (livelogs_webtv_positions_timer == INVALID_HANDLE)
        livelogs_webtv_positions_timer = CreateTimer(WEBTV_POSITION_UPDATE_RATE, updatePlayerPositionTimer, _, TIMER_REPEAT||TIMER_FLAG_NO_MAPCHANGE);
        
    return;
}

public Action:updatePlayerPositionTimer(Handle:timer, any:data)
{ 
    decl String:buffer[4096];
    
    FormatEx(buffer, sizeof(buffer), "O");
    
    new Float:p_origin[3], Float:p_angle[3]; //two vectors, one containing the position of the player and the other the angle the player is facing
    
    for (new i = 1; i <= MaxClients; i++)
    {
        if (IsClientInGame(i) && IsPlayerAlive(i) && !IsFakeClient(i))
        {
            if (strlen(buffer) > 1) //if more than just "O" is in the buffer, add separator
                Format(buffer, sizeof(buffer), "%s|", buffer); //player positions will be appended after an |
                
            GetClientAbsOrigin(i, p_origin);
            GetClientEyeAngles(i, p_angle);
            
            //we only need X and Y co-ords, and only need angle corresponding to the X Y plane
            Format(buffer, sizeof(buffer), "%s%d:%d:%d:%d", buffer, GetClientUserId(i), RoundToNearest(p_origin[0]), 
                                                RoundToNearest(p_origin[1]), RoundToNearest(p_angle[1]));
        }
    }
    
    if (strlen(buffer) == 1)
        return Plugin_Continue;
        
    addToWebBuffer(buffer);
    return Plugin_Continue;
}

public Action:webtv_bufferProcessTimer(Handle:timer, any:data)
{
    new Float:current_time = GetEngineTime(), Float:timediff;
    
    decl String:buf_split_array[3][4096];// String:strbuf[4096];
    
    for (new i = 0; i < livelogs_webtv_buffer_length; i++)
    {
        
        //if (DEBUG) { LogMessage("Processing buffer. Buf string: %s @ idx %d", livelogs_webtv_buffer[i], i); }
        
        //contains strings like timestamp@O3:blah:blah:blah
        new num_tok = ExplodeString(livelogs_webtv_buffer[i], "@", buf_split_array, 3, 4096); //now we have the timestamp and buffered data split
        
        //if we get 2 strings out of splitting, we have our timestap@msg
        if (num_tok >= 2)
        {        
            //compare timestamps to see if tv_delay has passed
            timediff = current_time - StringToFloat(buf_split_array[0]);
            
            if (timediff > webtv_delay) //i.e. delay seconds has past, time to send data
            {
                //if (DEBUG) { LogMessage("timestamp is outside of delay range. timediff: %f, sending. send msg: %s", timediff, buf_split_array[1]); }
                sendToAllWebChildren(buf_split_array[1]);
            }
            else 
            {
            //our timestamp is beyond the delay. therefore, everything following it will be as well. return before left shift
                return Plugin_Continue;
            }
            
            shiftBufferLeft(); //remove array element, also decrements buffer_length
            i--; //push our i down, because we removed an array element and hence shifted the index by << 1
        }
    }

    return Plugin_Continue;
}


public onWebSocketChildReceive(WebsocketHandle:sock, WebsocketSendType:send_type, const String:rcvd[], const dataSize)
{
    if (send_type != SendType_Text)
        return;
        
    if (DEBUG) { LogMessage("Child %d received msg %s (len: %d)", _:sock, rcvd, dataSize); }
    
    return;
        
}

public onWebSocketChildDisconnect(WebsocketHandle:sock)
{
    new client_index = FindValueInArray(livelogs_webtv_children, sock);
    
    if (client_index < 0)
        return;
    
    if (DEBUG) { LogMessage("child disconnect. client_index: %d", client_index); }
    
    RemoveFromArray(livelogs_webtv_children, client_index);
    RemoveFromArray(livelogs_webtv_children_ip, client_index);
    
    if (GetArraySize(livelogs_webtv_children) == 0 && livelogs_webtv_positions_timer != INVALID_HANDLE)
    {
        CloseHandle(livelogs_webtv_positions_timer);
        livelogs_webtv_positions_timer = INVALID_HANDLE;
    }
}
#endif

//------------------------------------------------------------------------------
// Clean up
//------------------------------------------------------------------------------

public OnMapEnd()
{
	endLogging(true);
    
    #if defined _websocket_included
    //notify connected clients of map end
    sendToAllWebChildren("MAP_END");

    if (livelogs_webtv_cleanup_timer != INVALID_HANDLE)
    {
        KillTimer(livelogs_webtv_cleanup_timer);
        livelogs_webtv_cleanup_timer = INVALID_HANDLE;
    }
    #endif
}

#if defined _websocket_included
public onWebSocketListenClose(WebsocketHandle:listen_sock)
{
    if (DEBUG) { LogMessage("webtv listen sock close"); }
    livelogs_webtv_listen_socket = INVALID_WEBSOCKET_HANDLE;
    
    new num_web_clients = GetArraySize(livelogs_webtv_children);
    if (num_web_clients == 0)
        return;
}

public onWebSocketListenError(WebsocketHandle:sock, const errorType, const errorNum)
{
    LogError("MASTER SOCKET ERROR: %d (errno %d)", errorType, errorNum);
    livelogs_webtv_listen_socket = INVALID_WEBSOCKET_HANDLE;
}


public onWebSocketChildError(WebsocketHandle:sock, const errorType, const errorNum)
{
    LogError("CHILD SOCKET ERROR: %d (err no %d)", errorType, errorNum);
    
    new client_index = FindValueInArray(livelogs_webtv_children, sock);
    
    if (client_index < 0)
        return;
    
    RemoveFromArray(livelogs_webtv_children, client_index);
    RemoveFromArray(livelogs_webtv_children_ip, client_index);
    
    if (GetArraySize(livelogs_webtv_children) == 0 && livelogs_webtv_positions_timer != INVALID_HANDLE)
    {
        CloseHandle(livelogs_webtv_positions_timer);
        livelogs_webtv_positions_timer = INVALID_HANDLE;
    }
}
#endif

//------------------------------------------------------------------------------
// Socket Functions
//------------------------------------------------------------------------------

public onSocketConnected(Handle:socket, any:arg)
{
    decl String:msg[256];

    ResetPack(arg); //arg is a datapack containing the message to send, need to get back to the starting position
    ReadPackString(arg, msg, sizeof(msg)); //msg now contains what we want to send

    SocketSend(socket, msg);
    if (DEBUG) { LogMessage("Sent data '%s'", msg); }
}

public onSocketReceive(Handle:socket, String:rcvd[], const dataSize, any:arg)
{
    //Livelogs response packet: LIVELOG!api_key!listener_address!listener_port!UNIQUE_IDENT OR REUSE
    if (DEBUG) { LogMessage("Data received: %s", rcvd); }

    decl String:ll_api_key[64];

    GetConVarString(livelogs_daemon_api_key, ll_api_key, sizeof(ll_api_key));

    decl String:split_buffer[5][64];
    new response_len = ExplodeString(rcvd, "!", split_buffer, 6, 64);
    
    //LogMessage("Num Toks: %d Tokenized params: 1 %s 2 %s 3 %s 4 %s 5 %s", response_len, split_buffer[0], split_buffer[1], split_buffer[2], split_buffer[3], split_buffer[4]);
    
    if (response_len == 5)
    {
        if (DEBUG) { LogMessage("Have tokenized response with len > 1. APIKEY: %s, SPECIFIED: %s", ll_api_key, split_buffer[1]); }

        if ((StrEqual("LIVELOG", split_buffer[0])) && (StrEqual(ll_api_key, split_buffer[1])))
        {            
            Format(listener_address, sizeof(listener_address), "%s:%s", split_buffer[2], split_buffer[3]);
            
            if (!StrEqual(split_buffer[4], "REUSE"))
            {
                if (DEBUG) { LogMessage("LL LOG_UNIQUE_IDENT: %s", split_buffer[4]); }
                strcopy(log_unique_ident, sizeof(log_unique_ident), split_buffer[4]);
            }
            
            ServerCommand("logaddress_add %s", listener_address);
            if (DEBUG) { LogMessage("Added address %s to logaddress list", listener_address); }
            
            #if defined _websocket_included
            
            //if the previous websocket is yet to be cleaned up, clean it up now
            cleanUpWebSocket();
            
            //now open websocket too
            if ((livelogs_webtv_listen_socket == INVALID_WEBSOCKET_HANDLE) && (webtv_library_present) && (webtv_enabled))
            {
                if (livelogs_webtv_cleanup_timer != INVALID_HANDLE)
                {
                    KillTimer(livelogs_webtv_cleanup_timer);
                    livelogs_webtv_cleanup_timer = INVALID_HANDLE;
                }

                webtv_delay = GetConVarFloat(livelogs_server_tv_delay);
                new webtv_lport = GetConVarInt(livelogs_webtv_listen_port);
                if (DEBUG) { LogMessage("websocket is present. initialising socket. Address: %s:%d", server_ip, webtv_lport); }
            
                livelogs_webtv_listen_socket = Websocket_Open(server_ip, webtv_lport, onWebSocketConnection, onWebSocketListenError, onWebSocketListenClose);
                
                livelogs_webtv_positions_timer = CreateTimer(WEBTV_POSITION_UPDATE_RATE, updatePlayerPositionTimer, _, TIMER_REPEAT|TIMER_FLAG_NO_MAPCHANGE);
            }
            #endif
        }
    }
    
    CloseHandle(socket); //don't need to do any more, close socket handle
}

public onSocketDisconnect(Handle:socket, any:arg)
{
	CloseHandle(socket);
	if (DEBUG) { LogMessage("Livelogs socket disconnected and closed"); }
}

public onSocketSendQueueEmpty(Handle:socket, any:arg) 
{
	//SocketDisconnect(socket);
	//CloseHandle(socket);
	if (DEBUG) { LogMessage("Send queue is empty"); }
}

public onSocketError(Handle:socket, const errorType, const errorNum, any:arg)
{
	LogError("SOCKET ERROR %d (errno %d)", errorType, errorNum);
	CloseHandle(socket);
}

public sendSocketData(String:msg[])
{
    new Handle:socket = SocketCreate(SOCKET_TCP, onSocketError);

    SocketSetSendqueueEmptyCallback(socket, onSocketSendQueueEmpty); //define the callback function for empty send queue

    decl String:ll_ip[64];

    GetConVarString(livelogs_daemon_address, ll_ip, sizeof(ll_ip));
    new ll_port = GetConVarInt(livelogs_daemon_port);

    new Handle:socket_pack = CreateDataPack();
    WritePackString(socket_pack, msg);

    SocketSetArg(socket, socket_pack);
    //Format(socketData, sizeof(socketData), "%s", msg);

    SocketConnect(socket, onSocketConnected, onSocketReceive, onSocketDisconnect, ll_ip, ll_port);

    if (DEBUG) { LogMessage("Attempting to connect to %s:%d)", ll_ip, ll_port); }
}

#if DEBUG
//Command for testing socket sending
public Action:Test_SockSend(client, args)
{
    if (client == 0)
	   requestListenerAddress();
}
#endif

//------------------------------------------------------------------------------
// Private functions
//------------------------------------------------------------------------------

clearVars()
{
    is_logging = false;
    live_on_restart = false;

    tournament_state[RED] = false;
    tournament_state[BLUE] = false;
}

requestListenerAddress()
{
    //SEND STRUCTURE: LIVELOG!123test!192.168.35.1!27015!cp_granary!John
    decl String:ll_request[256], String:ll_api_key[64], String:map[64], String:log_name[64];
    
    GetCurrentMap(map, sizeof(map));
    
    if (livelogs_ipgn_booking_name != INVALID_HANDLE)
    {
        GetConVarString(livelogs_ipgn_booking_name, log_name, sizeof(log_name));
    }
    else
    {
        GetConVarString(livelogs_server_name, log_name, sizeof(log_name));
    }
    
    GetConVarString(livelogs_daemon_api_key, ll_api_key, sizeof(ll_api_key));
    
    #if defined _websocket_included
    new webtv_port = GetConVarInt(livelogs_webtv_listen_port);
    if ((webtv_enabled) && (webtv_library_present))
    {
        Format(ll_request, sizeof(ll_request), "LIVELOG!%s!%s!%d!%s!%s!%d", ll_api_key, server_ip, server_port, map, log_name, webtv_port);  
    }
    else
    {
        Format(ll_request, sizeof(ll_request), "LIVELOG!%s!%s!%d!%s!%s", ll_api_key, server_ip, server_port, map, log_name);
    }
    #else
    Format(ll_request, sizeof(ll_request), "LIVELOG!%s!%s!%d!%s!%s", ll_api_key, server_ip, server_port, map, log_name);
    #endif
    sendSocketData(ll_request);
}

endLogging(bool:map_end = false)
{
    if (is_logging)
    {
        is_logging = false;

        ServerCommand("logaddress_del %s", listener_address);
    }
    
    #if defined _websocket_included
    if (map_end)
    {
        cleanUpWebSocket();
    }
    else
    {
        if ((webtv_library_present) && (livelogs_webtv_listen_socket != INVALID_WEBSOCKET_HANDLE))
        {
            livelogs_webtv_cleanup_timer = CreateTimer(GetConVarFloat(livelogs_server_tv_delay) + 10.0, cleanUpWebSocketTimer, TIMER_FLAG_NO_MAPCHANGE);
        }
    }
    #endif
}

bool:logOptionEnabled(option_value)
{
    /*
    option_value is a bitmask in the form of an int. we can use this to determine what logging options we should enable
    values:

    1 - damage taken
    2 - damage dealt
    4 - healing done
    8 - item pickups

    To set a level of logging the values are added together.
    */

    new bitmask = GetConVarInt(livelogs_logging_level); //a sum of whatever options are desired
    if (livelogs_bitmask_cache[option_value]) //if the cached value is true
    {
        return true; //just return true here
    }

    if ((option_value & bitmask) == option_value)
    {
        /*bitwise AND the option with the bitmask. if the option is one of the values summed to obtain the bitmask, the result is the option
        i.e 1 & 3 = 3, will return true, meaning damage taken is enabled. 
        2 & 3 = 2, will return true, meaning damage dealt is enabled.
        but 4 & 3 = 0, is false, so healing is disabled

        logic in binary:
        001 (1) & 011 (3) = 001 (1)
        010 (2) & 011 (3) = 010 (2)
        100 (4) & 011 (3) = 000 (0)
        1000 (8) & 011 (3) = 0000 (0)

        */
        livelogs_bitmask_cache[option_value] = true;

        return true;
    }
    else
    {
        livelogs_bitmask_cache[option_value] = false;
        return false;
    }

}

getConVarValues()
{
    //updates convars with values that are already set
    //i.e if logging is set to 0 on reload, the plugin will still think that it's set to 15 because of the reload

    log_additional_stats = GetConVarInt(livelogs_logging_level);
    create_new_log_file = GetConVarBool(livelogs_new_log_file);

#if defined _websocket_included
    webtv_enabled = GetConVarBool(livelogs_webtv_enabled);

#endif
}


stock _:ConVarExists(const String:cvar_name[])
{
    return FindConVar(cvar_name);
}

stock String:GetTFTeamName(index)
{
    //takes a GetClientTeam index, and returns a named team
    decl String:team[16];
    switch (index)
    {
        case 2:
            strcopy(team, sizeof(team), "Red");
        case 3:
            strcopy(team, sizeof(team), "Blue");
        default:
            strcopy(team, sizeof(team), "unknown");
    }

    return team;
}

#if defined _websocket_included
addToWebBuffer(const String:msg[])
{
    if (strlen(msg) < 1)
        return;
    
    
    if (livelogs_webtv_buffer_length >= MAX_BUFFER_SIZE-1)
    {
        if (DEBUG) { LogMessage("number of buffer items (%d) is >= the max buffer elements", livelogs_webtv_buffer_length); }

        //if this is occuring, perhaps the process timer is not active?
        if (livelogs_webtv_buffer_timer == INVALID_HANDLE)
        {
            if (DEBUG) { LogMessage("Buffer is full and process timer is not running. Starting process timer"); }
            livelogs_webtv_buffer_timer = CreateTimer(WEBTV_BUFFER_PROCESS_RATE, webtv_bufferProcessTimer, _, TIMER_REPEAT|TIMER_FLAG_NO_MAPCHANGE);
        }
        return;
    }
    
    new Float:time = GetEngineTime();
    
    new String:newbuffer[4096];
    FormatEx(newbuffer, sizeof(newbuffer), "%f@%s", time, msg); //append the timestamp to the msg
    
    strcopy(livelogs_webtv_buffer[livelogs_webtv_buffer_length], MAX_BUFFER_SIZE, newbuffer);
    livelogs_webtv_buffer_length++;
    
    //LogMessage("Added %s to send buffer. IN BUFFER: %s, INDEX: %d", newbuffer, livelogs_webtv_buffer[livelogs_webtv_buffer_length-1], livelogs_webtv_buffer_length-1);
    
    if (livelogs_webtv_buffer_timer == INVALID_HANDLE)
        livelogs_webtv_buffer_timer = CreateTimer(WEBTV_BUFFER_PROCESS_RATE, webtv_bufferProcessTimer, _, TIMER_REPEAT|TIMER_FLAG_NO_MAPCHANGE);
        
}

sendToAllWebChildren(const String:data[], num_web_clients = -1)
{
    if (num_web_clients == -1)
        num_web_clients = GetArraySize(livelogs_webtv_children);
    
    if (num_web_clients == 0)
        return;
    
    new WebsocketHandle:send_sock;
    
    for (new i = 0; i < num_web_clients; i++)
    {
        send_sock = WebsocketHandle:GetArrayCell(livelogs_webtv_children, i);
        
        //if (DEBUG) { LogMessage("data to be sent: %s", data); }
        
        if (Websocket_GetReadyState(send_sock) == State_Open)
            Websocket_Send(send_sock, SendType_Text, data);
    }
}

shiftBufferLeft()
{
    if (livelogs_webtv_buffer_length > MAX_BUFFER_SIZE)
    {   
        //need to chop it back down for left shift to work
        livelogs_webtv_buffer_length = MAX_BUFFER_SIZE;
    }

    for (new i = 0; i < livelogs_webtv_buffer_length; i++)
    {
        strcopy(livelogs_webtv_buffer[i], sizeof(livelogs_webtv_buffer[]), livelogs_webtv_buffer[i+1]);
    }
    livelogs_webtv_buffer_length--;
    //if (DEBUG) { LogMessage("left shift. buffer length: %d", livelogs_webtv_buffer_length); }
}

emptyWebBuffer()
{
    for (new i = 0; i < MAX_BUFFER_SIZE; i++)
    {
        strcopy(livelogs_webtv_buffer[i], sizeof(livelogs_webtv_buffer[]), "\0");
    }
    livelogs_webtv_buffer_length = 0;
    if (DEBUG) { LogMessage("cleared buffer"); }
}

cleanUpWebSocket()
{
    if (livelogs_webtv_listen_socket != INVALID_WEBSOCKET_HANDLE)
        Websocket_Close(livelogs_webtv_listen_socket);
        
        
    emptyWebBuffer();
    
    if (livelogs_webtv_buffer_timer != INVALID_HANDLE)
    {
        CloseHandle(livelogs_webtv_buffer_timer);
        livelogs_webtv_buffer_timer = INVALID_HANDLE;
    }
    if (livelogs_webtv_positions_timer != INVALID_HANDLE)
    {
        CloseHandle(livelogs_webtv_positions_timer);
        livelogs_webtv_positions_timer = INVALID_HANDLE;
    }
}

public Action:cleanUpWebSocketTimer(Handle:timer, any:data)
{
    cleanUpWebSocket();
        
    livelogs_webtv_cleanup_timer = INVALID_HANDLE;
    
    return Plugin_Stop;
}

#endif