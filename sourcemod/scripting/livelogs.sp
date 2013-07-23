/*
    Livelogs server plugin

    Copyright (C) 2012 Prithu "bladez" Parker

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>




    Credit to Carbon for basic structure of initiating actions on mp_tournament starts and ends
    To Jannik 'Peace-Maker' Hartung @ http://www.wcfan.de/ for basis of SourceTV2D
    To Cinq, Annuit Coeptis and Jean-Denis Caron for additional statistic logging such as damage done, heals, items and pausing/unpausing
*/

#define DEBUG true

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

#tryinclude <updater>

#if defined _updater_included
#define UPDATER_URL "http://livelogs.ozfortress.com/plugindata/patchinfo.txt"
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
	version = "0.6.6.1",
	url = "http://livelogs.ozfortress.com"
};



//------------------------------------------------------------------------------
// Variables
//------------------------------------------------------------------------------

new bool:tournament_state[2] = { false, false }; //Holds ready state for both teams
new bool:live_on_restart = false;
new bool:is_logging = false;
new bool:late_loaded;
new bool:livelogs_bitmask_cache[65];
new bool:create_new_log_file = false;
new bool:force_log_secret = true;
new bool:debug_enabled = true;

new String:server_ip[64];
new String:listener_address[128];
new String:log_unique_ident[128];
new String:client_index_cache[MAXPLAYERS+1][64];

new log_additional_stats;
new server_port;

//Handles for convars
new Handle:livelogs_daemon_address = INVALID_HANDLE; //ip/dns of livelogs daemon
new Handle:livelogs_daemon_port = INVALID_HANDLE; //port of livelogs daemon
new Handle:livelogs_daemon_api_key = INVALID_HANDLE; //the key that must be specified when communicating with the ll daemon
new Handle:livelogs_server_name = INVALID_HANDLE; //the name used for the server (as shown on the website)
new Handle:livelogs_logging_level = INVALID_HANDLE; //bitmask for logging levels
new Handle:livelogs_ipgn_booking_name = INVALID_HANDLE; //support ipgn's match recorder which uses names from a server booking bot
new Handle:livelogs_new_log_file = INVALID_HANDLE; //determine if this plugin should enable the server's logging functionality, or leave it to a config/other plugin
new Handle:livelogs_tournament_ready_only =  INVALID_HANDLE; //support the option of only logging when teams ready up, and not on mp_restartgame or equivalent command
new Handle:livelogs_force_logsecret = INVALID_HANDLE; //whether or not to set sv_logsecret
new Handle:livelogs_enable_debugging = INVALID_HANDLE; //toggle debug messages
new Handle:livelogs_enabled = INVALID_HANDLE; //enable/disable livelogs

new Handle:livelogs_tournament_mode_cache = INVALID_HANDLE; //for caching the mp_tournament cvar handle
new Handle:livelogs_mp_restartgame_cache = INVALID_HANDLE;
new Handle:livelogs_sv_logsecret_cache = INVALID_HANDLE; //cache sv_logsecret cvar

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

new Handle:livelogs_server_hostname_cache = INVALID_HANDLE; //for caching the hostname cvar handle
new Handle:livelogs_server_tv_delay_cache = INVALID_HANDLE; //for caching the tv_delay cvar handle

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
#if defined DEBUG
    RegConsoleCmd("test_livelogs", Test_SockSend);
#endif

    // Tournament state change
    HookEvent("tournament_stateupdate", tournamentStateChangeEvent);

    // Game restarted (mp_restartgame, or when tournament countdown ends)
    HookEvent("teamplay_restart_round", gameRestartEvent);

    //game over events
    HookEvent("tf_game_over", gameOverEvent); //mp_windifference_limit
    HookEvent("teamplay_game_over", gameOverEvent); //mp_maxrounds, mp_timelimit, mp_winlimit

    //Hook events for additional statistic display
    HookEvent("item_pickup", itemPickupEvent); //item is picked up
    HookEvent("player_hurt", playerHurtEvent); //player is hurt
    HookEvent("player_healed", playerHealEvent); //player receives healing, from dispenser or medic

    // Hook into mp_tournament_restart
    AddCommandListener(tournamentRestartHook, "mp_tournament_restart");

    // Hook mp_restartgame, mp_switchteams and mp_scrambleteams. ALl these commands restart the game completely, which means a new log file is required
    //mp_switchteams and mp_scrambleteams both use mp_restartgame
    livelogs_mp_restartgame_cache = FindConVar("mp_restartgame");
    HookConVarChange(livelogs_mp_restartgame_cache, conVarChangeHook); //this STUPID AS FUCK command is treated as a cvar for some FUCKED reason

    // Client commands
    RegConsoleCmd("sm_livelogs", urlCommandCallback, "Displays the livelogs log URL to the client");


    // Convars
    livelogs_daemon_address = CreateConVar("livelogs_address", "192.168.35.128", "IP or hostname of the livelogs daemon", FCVAR_PROTECTED|FCVAR_DONTRECORD|FCVAR_UNLOGGED);
    
    livelogs_daemon_port = CreateConVar("livelogs_port", "61222", "Port of the livelogs daemon", FCVAR_PROTECTED|FCVAR_DONTRECORD|FCVAR_UNLOGGED);
    
    livelogs_daemon_api_key = CreateConVar("livelogs_api_key", "123test", "API key for livelogs daemon", FCVAR_PROTECTED|FCVAR_DONTRECORD|FCVAR_UNLOGGED);

    livelogs_server_name = CreateConVar("livelogs_name", "default", "The name by which logs are identified on the website", FCVAR_PROTECTED);

    livelogs_logging_level = CreateConVar("livelogs_additional_logging", "15", "Set logging level. See FAQ/readme.txt for logging bitmask values",
                                            FCVAR_NOTIFY, true, 0.0, true, 64.0); //allows levels of logging via a bitmask

    livelogs_new_log_file = CreateConVar("livelogs_new_log_file", "0", "Whether to initiate console logging using 'log on'. Disable if you have another method of enabling logging", 
                                            FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_tournament_ready_only = CreateConVar("livelogs_tournament_ready_only", "0", "Whether livelogs should only log when teams ready up or not (mp_restartgame does not ready the teams up)", 
                                            FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_force_logsecret = CreateConVar("livelogs_force_logsecret", "1", "Whether livelogs should force sv_logsecret or not",
                                            FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_enable_debugging = CreateConVar("livelogs_enable_debugging", "1", "Enable or disable debug messages", FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_enabled = CreateConVar("livelogs_enabled", "1", "Enable or disable Livelogs", FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_tournament_mode_cache = FindConVar("mp_tournament"); //cache mp_tournament convar


    //Cache sv_logsecret
    livelogs_sv_logsecret_cache = FindConVar("sv_logsecret");

    // convar change hooks
    HookConVarChange(livelogs_new_log_file, conVarChangeHook);
    HookConVarChange(livelogs_logging_level, conVarChangeHook); //hook convar so we can change logging options on the fly
    HookConVarChange(livelogs_enable_debugging, conVarChangeHook);
    HookConVarChange(livelogs_force_logsecret, conVarChangeHook);


    //variables for later sending. we should get the IP via hostip, because people may not set "ip"
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
    
    livelogs_webtv_listen_port = CreateConVar("livelogs_webtv_port", default_web_port, "The port to listen on for SourceTV 2D connections. Defaults to server port + 2", FCVAR_PROTECTED);
    livelogs_webtv_enabled = CreateConVar("livelogs_enable_webtv", "1", "Toggle whether or not SourceTV2D will run",
                                    FCVAR_NOTIFY, true, 0.0, true, 1.0);


    livelogs_webtv_children = CreateArray();
    livelogs_webtv_children_ip = CreateArray(ByteCountToCells(33));

    livelogs_server_tv_delay_cache = FindConVar("tv_delay"); //cache the tv_delay convar handle

    //add event hooks and shiz for websocket, self explanatory names and event hooks
    HookEvent("player_team", playerTeamChangeEvent);
    HookEvent("player_death", playerDeathEvent);
    HookEvent("player_spawn", playerSpawnEvent);
    HookEvent("player_changeclass", playerClassChangeEvent);
    HookEvent("player_chargedeployed", playerUberEvent);
    HookEvent("teamplay_flag_event", playerFlagEvent);
    HookEvent("teamplay_round_start", roundStartEvent);
    HookEvent("teamplay_round_win", roundEndEvent);
    
    HookConVarChange(livelogs_webtv_enabled, websocketConVarChangeHook); //hook the webtv enable cvar, so we can enable/disable on the fly
    HookConVarChange(livelogs_server_tv_delay_cache, websocketConVarChangeHook); //hook tv_delay so we can adjust the delay dynamically
#endif

    if (late_loaded)
    {
        decl String:auth[64];
        for (new i = 1; i <= MaxClients; i++)
        {
            if (IsClientInGame(i) && IsClientAuthorized(i) && !IsFakeClient(i))
            {
                if (GetClientAuthString(i, auth, sizeof(auth)))
                {
                    OnClientAuthorized(i, auth); //call to onclientauth, which will cache the auth for us
                }
            }
        }
        
        //called by OnConfigsExecuted now getConVarValues(); //we need to get the value of convars that are already set if the plugin is loading late

        late_loaded = false;
    }

    AutoExecConfig(true, "livelogs", "");
}

public OnConfigsExecuted()
{
    getConVarValues();
}

public OnAllPluginsLoaded()
{
    //check convar settings & update
    if (!late_loaded)
    {
        getConVarValues();
    }

    if (livelogs_ipgn_booking_name == INVALID_HANDLE)
    {
        livelogs_ipgn_booking_name = ConVarExists("mr_ipgnbooker");
    }

#if defined _websocket_included
    if (LibraryExists("websocket"))
    {
        webtv_library_present = true;
        if (debug_enabled) { LogMessage("Websocket library present. Using SourceTV2D"); }
        
        cleanUpWebSocket();
    }
    else
        if (debug_enabled) { LogMessage("Websocket library is not present. Not using SourceTV2D"); }
#endif
#if defined _updater_included
    if (LibraryExists("updater"))
    {
        Updater_AddPlugin(UPDATER_URL);
    }
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

public OnLibraryAdded(const String:name[])
{
#if defined _websocket_included
    //this forward is only fired if websocket is added
    if (StrEqual(name, "websocket"))
    {
        webtv_library_present = true;
        cleanUpWebSocket();
    }
#endif
#if defined _updater_included
    if (StrEqual(name, "updater"))
    {
        Updater_AddPlugin(UPDATER_URL);
    }
#endif
}

#if defined _websocket_included
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
// Callbacks and hooks (non-webtv)
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

public conVarChangeHook(Handle:cvar, const String:oldval[], const String:newval[])
{
    /*
    ConVar handles:
    HookConVarChange(livelogs_new_log_file, conVarChangeHook);
    HookConVarChange(livelogs_logging_level, conVarChangeHook); //hook convar so we can change logging options on the fly
    HookConVarChange(livelogs_enable_debugging, conVarChangeHook);
    HookConVarChange(livelogs_mp_restartgame_cache, conVarChangeHook);
    */

    if (cvar == livelogs_new_log_file)
    {
        create_new_log_file = GetConVarBool(cvar);

        if (create_new_log_file)
        {
            PrintToServer("Livelogs will enable logging (create a new log file) using 'log on' on match start");
        }
        else
        {
            PrintToServer("Livelogs will not enable console log output on match start (no 'log on'). Ensure you have another method of enabling console logging");
        }
    }
    else if (cvar == livelogs_logging_level)
    {
        log_additional_stats = GetConVarInt(cvar);

        if (log_additional_stats > 0)
        {
            PrintToServer("Livelogs now outputting additional logging");
        }
        else
        {
            PrintToServer("Livelogs no longer outputting additional statistics");
        }

        //recache bitmask
        for (new i = 1; i < sizeof(livelogs_bitmask_cache); i++)
        {
            logOptionEnabled(i);
        }
    }
    else if (cvar == livelogs_enable_debugging)
    {
        debug_enabled = GetConVarBool(cvar);

        if (debug_enabled)
        {
            PrintToServer("Livelogs debug messages enabled");
        }
        else
        {
            PrintToServer("Livelogs debug messages disabled");
        }
    }
    else if (cvar == livelogs_mp_restartgame_cache)
    {
        if (debug_enabled) { LogMessage("mp_restartgame changed. old: %s, new %s", oldval, newval); }
        new restart_time = GetConVarInt(cvar);

        if ((restart_time > 0) && (!live_on_restart)) //prevent multiple mp_restartgames starting/ending logs
        {
            //we have a restart command!
            newLogOnRestartCheck();
        }
    }
    else if (cvar == livelogs_force_logsecret)
    {
        if (force_log_secret)
        {
            PrintToServer("Livelogs will not force sv_logsecret");
            force_log_secret = false;
        }
        else
        {
            PrintToServer("Livelogs will force sv_logsecret");
            force_log_secret = true;
        }
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
        if (GetConVarInt(livelogs_enabled))
        {
            if (create_new_log_file)
            {
                ServerCommand("log on"); //create new log file, enable console log output
            }

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

        if (!GetClientName(clientidx, player_name, sizeof(player_name)))
        {
            return;
        }

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

public Action:restartCommandHook(client, const String:command[], arg)
{
    //one of the restart commands was used (mp_switchteams/mp_scrambleteams)
    newLogOnRestartCheck();
}

//---------------------------
//Include all the sourcetv2d event hooks, timers and functions
//---------------------------
#if defined _websocket_included
#include "livelogs_websocket.sp"
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

//------------------------------------------------------------------------------
// Socket Functions
//------------------------------------------------------------------------------

public onSocketConnected(Handle:socket, any:arg)
{
    decl String:msg[256];

    ResetPack(arg); //arg is a datapack containing the message to send, need to get back to the starting position
    ReadPackString(arg, msg, sizeof(msg)); //msg now contains what we want to send

    SocketSend(socket, msg);
    if (debug_enabled) { LogMessage("Sent data '%s'", msg); }
}

public onSocketReceive(Handle:socket, String:rcvd[], const dataSize, any:arg)
{
    //Livelogs response packet: LIVELOG!api_key!listener_address!listener_port!UNIQUE_IDENT OR REUSE
    if (debug_enabled) { LogMessage("Data received: %s", rcvd); }


    if (StrEqual("INVALID_API_KEY", rcvd))
    {

        if (debug_enabled) { LogMessage("Invalid API key specified"); }

        CloseHandle(socket);
        return;
    }

    decl String:ll_api_key[128];

    GetConVarString(livelogs_daemon_api_key, ll_api_key, sizeof(ll_api_key));

    decl String:split_buffer[5][64];
    new response_len = ExplodeString(rcvd, "!", split_buffer, 6, 64);
    
    //LogMessage("Num Toks: %d Tokenized params: 1 %s 2 %s 3 %s 4 %s 5 %s", response_len, split_buffer[0], split_buffer[1], split_buffer[2], split_buffer[3], split_buffer[4]);
    
    if (response_len == 5)
    {
        if (debug_enabled) { LogMessage("Have tokenized response with len > 1. APIKEY: %s, SPECIFIED: %s", ll_api_key, split_buffer[1]); }

        if ((StrEqual("LIVELOG", split_buffer[0])) && (StrEqual(ll_api_key, split_buffer[1])))
        {            
            Format(listener_address, sizeof(listener_address), "%s:%s", split_buffer[2], split_buffer[3]);
            
            if (!StrEqual(split_buffer[4], "REUSE"))
            {
                if (debug_enabled) { LogMessage("LL LOG_UNIQUE_IDENT: %s", split_buffer[4]); }
                strcopy(log_unique_ident, sizeof(log_unique_ident), split_buffer[4]);
            }

            decl String:log_secret[128];
            if (livelogs_sv_logsecret_cache != INVALID_HANDLE && !force_log_secret)
            {   
                /* 
                A log secret is already set, and we don't want to force a log secret
                Therefore, we use what is currently set if it's not 0 or null
                */
                GetConVarString(livelogs_sv_logsecret_cache, log_secret, sizeof(log_secret));
                if (strlen(log_secret) <= 1 || StrEqual("0", log_secret))
                {
                    /* don't want to use this key as a secret, it's too short or is default '0' */
                    strcopy(log_secret, sizeof(log_secret), ll_api_key); //use api key as secret
                }
            }
            else
            {
                /* logsecret cache is either an invalid handle, or we want to force the log secret */
                strcopy(log_secret, sizeof(log_secret), ll_api_key); //use api key as secret
            }

            decl String:tmp[129];
            if (force_log_secret && !IsCharNumeric(log_secret[0]))
            {
                /* if the first char of the log secret is not numeric, append a number to it so that logsecret works */
                strcopy(tmp, sizeof(tmp), "1");
                StrCat(tmp, sizeof(tmp), log_secret); /* append a 1 to the string */
                strcopy(log_secret, sizeof(log_secret), tmp);
            }

            ServerCommand("sv_logsecret %s; logaddress_add %s", log_secret, listener_address);
            if (debug_enabled) { LogMessage("Added address %s to logaddress list", listener_address); }
            
        #if defined _websocket_included
            
            //if the previous websocket is yet to be cleaned up, clean it up now
            cleanUpWebSocket();
            
            //now open new websocket
            if ((webtv_library_present) && (webtv_enabled) && (livelogs_webtv_listen_socket == INVALID_WEBSOCKET_HANDLE))
            {
                if (livelogs_webtv_cleanup_timer != INVALID_HANDLE)
                {
                    KillTimer(livelogs_webtv_cleanup_timer);
                    livelogs_webtv_cleanup_timer = INVALID_HANDLE;
                }

                webtv_delay = GetConVarFloat(livelogs_server_tv_delay_cache);
                new webtv_lport = GetConVarInt(livelogs_webtv_listen_port);
                if (debug_enabled) { LogMessage("websocket is present. initialising socket. Address: %s:%d", server_ip, webtv_lport); }
            
                livelogs_webtv_listen_socket = Websocket_Open(server_ip, webtv_lport, onWebSocketConnection, onWebSocketListenError, onWebSocketListenClose);
                
                livelogs_webtv_positions_timer = CreateTimer(WEBTV_POSITION_UPDATE_RATE, updatePlayerPositionTimer, _, TIMER_REPEAT|TIMER_FLAG_NO_MAPCHANGE);
            }
        #endif
        }
        else
        {
            if (debug_enabled) { LogMessage("Invalid message returned by server"); }
        }
    }
    
    CloseHandle(socket); //don't need to do any more, close socket handle
}

public onSocketDisconnect(Handle:socket, any:arg)
{
	CloseHandle(socket);
	if (debug_enabled) { LogMessage("Livelogs socket disconnected and closed"); }
}

public onSocketSendQueueEmpty(Handle:socket, any:arg) 
{
	//SocketDisconnect(socket);
	//CloseHandle(socket);
	if (debug_enabled) { LogMessage("Send queue is empty"); }
}

public onSocketError(Handle:socket, const errorType, const errorNum, any:arg)
{
	LogError("SOCKET ERROR %d (errno %d)", errorType, errorNum);
	CloseHandle(socket);
}

public sendSocketData(String:msg[])
{
    new Handle:socket = SocketCreate(SOCKET_TCP, onSocketError);


    new bind_port = 50000;
    new bool:socket_bound = false;

    while ((!socket_bound) && (bind_port < 65000))
    {
        if (!SocketBind(socket, server_ip, bind_port))
        {
            if (debug_enabled) { LogMessage("ERROR: Unable to bind request socket to port %d", bind_port); }

            bind_port += 1;
        }
        else
        {
            socket_bound = true;
        }
        
    }

    //if the socket still isn't bound after the loop, we need to return
    if (!socket_bound)
    {
        if (debug_enabled) { LogMessage("ERROR: Unable to bind request socket. Not getting logger details"); }
        CloseHandle(socket);
        return;
    }

    SocketSetSendqueueEmptyCallback(socket, onSocketSendQueueEmpty); //define the callback function for empty send queue

    decl String:ll_ip[64];

    GetConVarString(livelogs_daemon_address, ll_ip, sizeof(ll_ip));
    new ll_port = GetConVarInt(livelogs_daemon_port);

    new Handle:socket_pack = CreateDataPack();
    WritePackString(socket_pack, msg);

    SocketSetArg(socket, socket_pack);
    //Format(socketData, sizeof(socketData), "%s", msg);

    SocketConnect(socket, onSocketConnected, onSocketReceive, onSocketDisconnect, ll_ip, ll_port);

    if (debug_enabled) { LogMessage("Attempting to connect to %s:%d)", ll_ip, ll_port); }
}

#if defined DEBUG
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
    decl String:ll_request[256], String:ll_api_key[64], String:map[64], String:log_name[64], String:log_secret[128];
    
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

    if (livelogs_sv_logsecret_cache == INVALID_HANDLE)
    {
        livelogs_sv_logsecret_cache = FindConVar("sv_logsecret");
    }

    if (livelogs_sv_logsecret_cache != INVALID_HANDLE && !force_log_secret)
    {   
        /* 
        A log secret is already set, and we don't want to force a log secret
        Therefore, we use what is currently set if it's not 0 or null
        */
        GetConVarString(livelogs_sv_logsecret_cache, log_secret, sizeof(log_secret));
        if (strlen(log_secret) <= 1 || StrEqual("0", log_secret))
        {
            /* don't want to use this key as a secret, it's too short or is default '0' */
            strcopy(log_secret, sizeof(log_secret), ll_api_key); //use api key as secret
        }
    }
    else
    {
        /* logsecret cache is either an invalid handle, or we want to force the log secret */
        strcopy(log_secret, sizeof(log_secret), ll_api_key); //use api key as secret
    }

    decl String:tmp[129];
    if (force_log_secret && !IsCharNumeric(log_secret[0]))
    {
        /* if the first char of the log secret is not numeric, append a number to it so that logsecret works */
        strcopy(tmp, sizeof(tmp), "1");
        StrCat(tmp, sizeof(tmp), log_secret); /* append a 1 to the string */
        strcopy(log_secret, sizeof(log_secret), tmp);
    }
            
    
#if defined _websocket_included
    new webtv_port = GetConVarInt(livelogs_webtv_listen_port);
    if ((webtv_enabled) && (webtv_library_present))
    {
        Format(ll_request, sizeof(ll_request), "LIVELOG!%s!%s!%d!%s!%s!%d", ll_api_key, log_secret, server_port, map, log_name, webtv_port);  
    }
    else
    {
        Format(ll_request, sizeof(ll_request), "LIVELOG!%s!%s!%d!%s!%s", ll_api_key, log_secret, server_port, map, log_name);
    }
#else
    Format(ll_request, sizeof(ll_request), "LIVELOG!%s!%s!%d!%s!%s", ll_api_key, log_secret, server_port, map, log_name);
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
            livelogs_webtv_cleanup_timer = CreateTimer(GetConVarFloat(livelogs_server_tv_delay_cache) + 10.0, cleanUpWebSocketTimer, TIMER_FLAG_NO_MAPCHANGE);
        }
    }
    #endif
}

newLogOnRestartCheck()
{
    //called by the callbacks for restart commands (mp_restartgame, mp_switchteams, mp_scrambleteams)
    if (debug_enabled) { LogMessage("Restart command. treadyonly: %d, mp_tournament: %d", GetConVarBool(livelogs_tournament_ready_only), GetConVarBool(livelogs_tournament_mode_cache)); }

    if (is_logging)
    {
        if (debug_enabled) { LogMessage("Restart command issued while currently logging. Ending log"); }
        LogToGame("\"LIVELOG_GAME_RESTART\""); //tell the daemon that the current log needs to be closed, so a new one can be opened
        endLogging();

        //if we're already logging, we should be logging on a restart too
        live_on_restart = true;
    }
    else
    {
        //check whether we should only start logging on tournament ready or not
        if (!GetConVarBool(livelogs_tournament_ready_only) && GetConVarBool(livelogs_tournament_mode_cache))
        {
            /*
            Since logging isn't just enabled on tournament ready, we should start logging on the next restart (provided mp_tournament is set)

            This means that an mp_restartgame that is initiated without teams readying up will still start logs properly
            */
            if (debug_enabled) { LogMessage("logging will start on next restart"); }

            live_on_restart = true;
        }
    }
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
    debug_enabled = GetConVarBool(livelogs_enable_debugging);
    force_log_secret = GetConVarBool(livelogs_force_logsecret);

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
