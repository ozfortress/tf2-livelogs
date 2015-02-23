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




    Credit to:
    * Carbon for basic structure of initiating actions on mp_tournament starts and ends
    * Jannik 'Peace-Maker' Hartung @ http://www.wcfan.de/ for basis of SourceTV2D
    * Cinq, Annuit Coeptis and Jean-Denis Caron for additional statistic logging
      such as damage done, heals, items and pausing/unpausing
    * F2 for medic buff recording (http://etf2l.org/forum/customise/topic-27485/page-1/#post-476085)
      and real damage
*/

#define DEBUG true

#define BUFF_TIMER_INTERVAL 0.5 //every half a second

#pragma semicolon 1 //must use semicolon to end lines

#include <sourcemod>
#include <socket>
#include <sdktools>
#include <tf2_stocks>

#include <livelogs>

#undef REQUIRE_PLUGIN

#tryinclude <updater>

#if defined _updater_included
#define UPDATER_URL "http://livelogs.ozfortress.com/plugindata/patchinfo.txt"
#endif

public Plugin:myinfo =
{
    name = "Livelogs",
	author = "Prithu \"bladez\" Parker",
	description = "Server-side plugin for the livelogs system. Sends logging request to the livelogs daemon and instigates logging procedures",
	version = "0.7.1",
	url = "http://livelogs.ozfortress.com"
};



//------------------------------------------------------------------------------
// Variables
//------------------------------------------------------------------------------

new bool:tournament_state[2] = { false, false }; //Holds ready state for both teams
new bool:live_on_restart = false;
new bool:is_logging = false;
new bool:late_loaded;
new bool:log_overheal = true;
new bool:create_new_log_file = false;
new bool:force_log_secret = true;
new bool:debug_enabled = true;
new bool:show_motd_panel = false;

new String:server_ip[64];
new String:listener_address[128];
new String:log_unique_ident[128];
new String:client_auth_cache[MAXPLAYERS+1][64];

new server_port;

// required for recording medic buffing
new client_lasthealth[MAXPLAYERS+1];
new client_maxhealth[MAXPLAYERS+1];
new client_healtarget[MAXPLAYERS+1]; //each value is the medic id who is targetting this client

//Handles for convars
new Handle:livelogs_daemon_address = INVALID_HANDLE; //ip/dns of livelogs daemon
new Handle:livelogs_daemon_port = INVALID_HANDLE; //port of livelogs daemon
new Handle:livelogs_daemon_api_key = INVALID_HANDLE; //the key that must be specified when communicating with the ll daemon
new Handle:livelogs_server_name = INVALID_HANDLE; //the name used for the server (as shown on the website)
new Handle:livelogs_new_log_file = INVALID_HANDLE; //determine if this plugin should enable the server's logging functionality, or leave it to a config/other plugin
new Handle:livelogs_tournament_ready_only =  INVALID_HANDLE; //support the option of only logging when teams ready up, and not on mp_restartgame or equivalent command
new Handle:livelogs_force_logsecret = INVALID_HANDLE; //whether or not to set sv_logsecret
new Handle:livelogs_enable_debugging = INVALID_HANDLE; //toggle debug messages
new Handle:livelogs_enabled = INVALID_HANDLE; //enable/disable livelogs
new Handle:livelogs_panel_display = INVALID_HANDLE; //whether to show !livelogs as a url or a panel
new Handle:livelogs_log_overheal = INVALID_HANDLE; //whether to record real damage or default damage

new Handle:livelogs_buff_timer = INVALID_HANDLE; //a timer for checking medic buff amounts

new Handle:livelogs_tournament_mode_cache = INVALID_HANDLE; //for caching the mp_tournament cvar handle
new Handle:livelogs_mp_restartgame_cache = INVALID_HANDLE;
new Handle:livelogs_sv_logsecret_cache = INVALID_HANDLE; //cache sv_logsecret cvar

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
    HookEvent("teamplay_ready_restart", gameRestartEvent);

    // round start
    HookEvent("teamplay_round_start", roundStartEvent_Log);


    //game over events
    HookEvent("tf_game_over", gameOverEvent); //mp_windifference_limit
    HookEvent("teamplay_game_over", gameOverEvent); //mp_maxrounds, mp_timelimit, mp_winlimit

    //Hook player spawn for buffs
    HookEvent("player_spawn", playerSpawnEvent_Log);

    // Hook into mp_tournament_restart
    AddCommandListener(tournamentRestartHook, "mp_tournament_restart");

    // Hook mp_restartgame, mp_switchteams and mp_scrambleteams. ALl these commands restart the game completely, which means a new log file is required
    //mp_switchteams and mp_scrambleteams both use mp_restartgame
    livelogs_mp_restartgame_cache = FindConVar("mp_restartgame");
    HookConVarChange(livelogs_mp_restartgame_cache, conVarChangeHook); //this STUPID AS FUCK command is treated as a cvar for some FUCKED reason

    // Client commands
    RegConsoleCmd("sm_livelogs", urlCommandCallback, "Displays the livelogs log URL to the client");


    // Convars
    livelogs_daemon_address = CreateConVar("livelogs_address", "192.168.35.128", "IP or hostname of the livelogs daemon", 
                                        FCVAR_PROTECTED|FCVAR_DONTRECORD|FCVAR_UNLOGGED);
    
    livelogs_daemon_port = CreateConVar("livelogs_port", "61222", "Port of the livelogs daemon", 
                                    FCVAR_PROTECTED|FCVAR_DONTRECORD|FCVAR_UNLOGGED);
    
    livelogs_daemon_api_key = CreateConVar("livelogs_api_key", "123test", "API key for livelogs daemon", 
                                    FCVAR_PROTECTED|FCVAR_DONTRECORD|FCVAR_UNLOGGED);

    livelogs_server_name = CreateConVar("livelogs_name", "default", "The name by which logs are identified on the website", 
                                    FCVAR_PROTECTED);

    livelogs_new_log_file = CreateConVar("livelogs_new_log_file", "0", 
                                    "Whether to initiate console logging using 'log on'. Disable if you have another method of enabling logging", 
                                    FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_tournament_ready_only = CreateConVar("livelogs_tournament_ready_only", "0", 
                                            "Whether livelogs should only log when teams ready up or not (mp_restartgame does not ready the teams up)", 
                                            FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_force_logsecret = CreateConVar("livelogs_force_logsecret", "1", "Whether livelogs should force sv_logsecret or not",
                                            FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_enable_debugging = CreateConVar("livelogs_enable_debugging", "1", "Enable or disable debug messages", 
                                        FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_enabled = CreateConVar("livelogs_enabled", "1", "Enable or disable Livelogs", 
                            FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_panel_display = CreateConVar("livelogs_panel", "0", "Whether to show logs in a panel or give a URL", 
                                    FCVAR_NOTIFY, true, 0.0, true, 1.0);

    livelogs_tournament_mode_cache = FindConVar("mp_tournament"); //cache mp_tournament convar

    livelogs_log_overheal = CreateConVar("livelogs_log_overheal", "1", "Whether or not to log overhealing", 
                                FCVAR_NOTIFY, true, 0.0, true, 1.0);


    //Cache sv_logsecret
    livelogs_sv_logsecret_cache = FindConVar("sv_logsecret");

    // convar change hooks
    HookConVarChange(livelogs_new_log_file, conVarChangeHook);
    HookConVarChange(livelogs_enable_debugging, conVarChangeHook);
    HookConVarChange(livelogs_force_logsecret, conVarChangeHook);
    HookConVarChange(livelogs_panel_display, conVarChangeHook);
    HookConVarChange(livelogs_log_overheal, conVarChangeHook);


    //variables for later sending. we should get the IP via hostip, because people may not set "ip"
    new longip = GetConVarInt(FindConVar("hostip")), ip_quad[4];
    ip_quad[0] = (longip >> 24) & 0x000000FF;
    ip_quad[1] = (longip >> 16) & 0x000000FF;
    ip_quad[2] = (longip >> 8) & 0x000000FF;
    ip_quad[3] = (longip) & 0x000000FF;
    
    Format(server_ip, sizeof(server_ip), "%d.%d.%d.%d", ip_quad[0], ip_quad[1], ip_quad[2], ip_quad[3]);
    
    server_port = GetConVarInt(FindConVar("hostport"));

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

                // Fix up healths for overhealing
                client_maxhealth[i] = GetClientHealth(i);
                client_lasthealth[i] = client_maxhealth[i];
            }
        }
        
        activateBuffTimer();
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
    if (late_loaded)
    {
        getConVarValues();
        late_loaded = false;
    }

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

}

public OnLibraryAdded(const String:name[])
{
#if defined _updater_included
    if (StrEqual(name, "updater"))
    {
        Updater_AddPlugin(UPDATER_URL);
    }
#endif
}

//------------------------------------------------------------------------------
// Callbacks and hooks
//------------------------------------------------------------------------------

public OnClientAuthorized(client, const String:auth[])
{
    //cache the client's steam id, for performance in event hooks
    strcopy(client_auth_cache[client], sizeof(client_auth_cache[]), auth);
}

public OnClientDisconnect(client)
{
    strcopy(client_auth_cache[client], sizeof(client_auth_cache[]), "\0"); //clear client's steamid
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
        new String:ll_url[128];
        Format(ll_url, sizeof(ll_url), "http://livelogs.ozfortress.com/view/%s", log_unique_ident);

        if (show_motd_panel)
        {
            ShowMOTDPanel(client, "Livelogs", ll_url, MOTDPANEL_TYPE_URL);
        }
            
        PrintToChat(client, "Log URL: %s", ll_url);
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
    HookConVarChange(livelogs_panel_display, conVarChangeHook);
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
    else if (cvar == livelogs_log_overheal)
    {
        log_overheal = GetConVarBool(cvar);

        if (log_overheal)
        {
            PrintToServer("Livelogs is now logging overhealing");
            activateBuffTimer();
        }
        else 
        {
            PrintToServer("Livelogs is no longer logging overhealing");
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
        force_log_secret = GetConVarBool(cvar);
        if (force_log_secret)
        {
            PrintToServer("Livelogs will force sv_logsecret");
        }
        else
        {
            PrintToServer("Livelogs will not force sv_logsecret");
        }
    }
    else if (cvar == livelogs_panel_display)
    {
        show_motd_panel = GetConVarBool(cvar);
        if (show_motd_panel)
        {
            PrintToServer("Livelogs will now display !livelogs in a panel");
        }
        else
        {
            PrintToServer("Livelogs will no longer display !livelogs in a panel");
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
    if (live_on_restart && !is_logging)
    {
        if (GetConVarBool(livelogs_enabled))
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

public roundStartEvent_Log(Handle:event, const String:name[], bool:dontBroadcast)
{
    new bool:full_reset = GetEventBool(event, "full_reset");

    if (debug_enabled) { LogMessage("teamplay_round_start event. full_reset: %d", full_reset); }
}

public gameOverEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
	endLogging(); //stop the logging -- does this really need to be done? hmmm
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

public playerSpawnEvent_Log(Handle:event, const String:name[], bool:dontBroadcast)
{
    new userid = GetEventInt(event, "userid");
    new client = GetClientOfUserId(userid);

    client_maxhealth[client] = GetClientHealth(client);
    client_lasthealth[client] = client_maxhealth[client];
}

public Action:getMedicBuffs(Handle:timer, any:data)
{
    //If medic buffing recording isn't enabled, just kill the timer
    if (!log_overheal)
    {
        livelogs_buff_timer = INVALID_HANDLE;
        return Plugin_Stop;
    }
    // get medic targets
    for (new i = 1; i <= MaxClients; i++)
    {
        if (IsClientConnected(i) && IsClientInGame(i) && (!IsFakeClient(i)))
        {
            if (TF2_GetPlayerClass(i) == TFClass_Medic)
            {
                new target = TF2_GetHealingTarget(i);

                // add this target to the array if it is a valid target
                // the array stores the index of the medic corresponding
                // to the target index
                // i.e client_healtarget[player] = medic means that the last
                // (known) healer for player was medic. 
                // 
                // if multiple medics heal the same target, only the
                // last checked medic will be recorded
                if (target > 0)
                    client_healtarget[target] = i;
            }
        }
    }

    // check every clients buffs
    for (new i = 1; i <= MaxClients; i++)
    {
        // client was last considered dead or is not a valid player
        if (client_lasthealth[i] <= 0)
            continue;
        
        // if this matches, client is not a valid player
        if (!IsClientConnected(i) || !IsClientInGame(i) || IsFakeClient(i))
        {
            client_lasthealth[i] = 0;
            continue;
        }

        // player is not alive, cannot be buffed
        if (!IsPlayerAlive(i))
            continue;

        // check current health against player's last health
        new currhealth = GetClientHealth(i);
        new prevhealth = client_lasthealth[i];
        new maxhealth = client_maxhealth[i];

        new buffamount = 0;

        // if the player has more health now than previously and
        // currhealth > maxhealth, then the player has some more overheal
        if (currhealth > prevhealth && currhealth > maxhealth)
            buffamount = currhealth - ( prevhealth > maxhealth ? prevhealth : maxhealth );

        // update the last health to the current health for the next check
        client_lasthealth[i] = currhealth;

        // if the player has been buffed this check, log it!
        if (buffamount > 0)
            LogOverHeal(i, buffamount);   
    }

    return Plugin_Continue;
}

//------------------------------------------------------------------------------
// Clean up
//------------------------------------------------------------------------------

public OnMapEnd()
{
    endLogging(true);

    if (livelogs_buff_timer != INVALID_HANDLE)
    {
        KillTimer(livelogs_buff_timer);
        livelogs_buff_timer = INVALID_HANDLE;
    }
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

            SetConVarString(livelogs_sv_logsecret_cache, log_secret);

            ServerCommand("logaddress_add %s", listener_address);
            if (debug_enabled) { LogMessage("Added address %s to logaddress list", listener_address); }

            //start the buff timer check
            activateBuffTimer();

            // log a message to indicate the game has started?
            LogToGame("\"LIVELOG_LOGGING_START\"");
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

    new String:ll_ip[64];

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
    //SEND STRUCTURE: LIVELOG!APIKEY!LOGSECRET!SPORT!MAP!LOGNAME!WEBTVPORT
    decl String:ll_request[256], String:ll_api_key[64], String:map[64], String:log_name[64], String:log_secret[128];
    
    GetCurrentMap(map, sizeof(map));
    

    GetConVarString(livelogs_server_name, log_name, sizeof(log_name));
    
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
        /* if the first char of the log secret is not numeric, prepend a number to it so that logsecret works */
        strcopy(tmp, sizeof(tmp), "1");
        StrCat(tmp, sizeof(tmp), log_secret); /* prepend a 1 to the string */
        strcopy(log_secret, sizeof(log_secret), tmp);
    }
            
    
    Format(ll_request, sizeof(ll_request), "LIVELOG!%s!%s!%d!%s!%s", ll_api_key, log_secret, server_port, map, log_name);

    sendSocketData(ll_request);
}

endLogging(bool:map_end = false)
{
    if (is_logging)
    {
        is_logging = false;

        LogToGame("\"LIVELOG_GAME_END\""); //send a game end message, in-case game over isn't triggered or w/e
        ServerCommand("logaddress_del %s", listener_address);
    }

    if (livelogs_buff_timer != INVALID_HANDLE)
    {
        KillTimer(livelogs_buff_timer);
        livelogs_buff_timer = INVALID_HANDLE;
    }
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

getConVarValues()
{
    //updates convars with values that are already set
    //i.e if logging is set to 0, on reload the plugin will think that it's set to 15 because of the reload

    create_new_log_file = GetConVarBool(livelogs_new_log_file);
    debug_enabled = GetConVarBool(livelogs_enable_debugging);
    force_log_secret = GetConVarBool(livelogs_force_logsecret);
    show_motd_panel = GetConVarBool(livelogs_panel_display);
    log_overheal = GetConVarBool(livelogs_log_overheal);
}

activateBuffTimer()
{
    if (!log_overheal) return;

    if (livelogs_buff_timer == INVALID_HANDLE)
        livelogs_buff_timer = CreateTimer(BUFF_TIMER_INTERVAL, getMedicBuffs, _, 
                                          TIMER_REPEAT|TIMER_FLAG_NO_MAPCHANGE);
}

// log this event, and only this event, outside of the hook because the hook is
// already fucking gigantic
LogOverHeal(patient_idx, amount)
{
    decl String:healer_name[MAX_NAME_LENGTH], String:healer_auth[64], String:healer_team[16];
    decl String:patient_name[MAX_NAME_LENGTH], String:patient_auth[64], String:patient_team[16];

    new healer_idx = client_healtarget[patient_idx];
    
    // if this player's healer is unknown, skip it
    if (healer_idx <= 0) {
        return;
    } 

    new healerid = GetClientUserId(healer_idx);
    new patientid = GetClientUserId(patient_idx);

    if (!GetClientName(healer_idx, healer_name, sizeof(healer_name))) return;
    if (!GetClientName(patient_idx, patient_name, sizeof(patient_name))) return;

    strcopy(healer_auth, sizeof(healer_auth), client_auth_cache[healer_idx]);
    strcopy(patient_auth, sizeof(patient_auth), client_auth_cache[patient_idx]);

    GetTeamName(GetClientTeam(healer_idx), healer_team, sizeof(healer_team));
    GetTeamName(GetClientTeam(patient_idx), patient_team, sizeof(patient_team));

    LogToGame("\"%s<%d><%s><%s>\" triggered \"overhealed\" against \"%s<%d><%s><%s>\" (overhealing \"%d\")",
            healer_name,
            healerid,
            healer_auth,
            healer_team,
            patient_name,
            patientid,
            patient_auth,
            patient_team,
            amount
        );
}

// Credit to F2 for this stock
stock TF2_GetHealingTarget(client) 
{
    new String:classname[64];
    new index = GetEntPropEnt(client, Prop_Send, "m_hActiveWeapon");
    if (index > 0) {
        GetEntityNetClass(index, classname, sizeof(classname));
    
        if(StrEqual(classname, "CWeaponMedigun")) {
            if(GetEntProp(index, Prop_Send, "m_bHealing") == 1)
                return GetEntPropEnt(index, Prop_Send, "m_hHealingTarget");
        }
    }
    
    return -1;
}

