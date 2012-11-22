/*
    Credit goes to Carbon for basic structure of initiating actions on mp_tournament starts and ends
    To Jannik 'Peace-Maker' Hartung @ http://www.wcfan.de/ for basis of SourceTV2D
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
 * I: Initial child socket connect. Sends game and map
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


#include <sourcemod>
#include <socket>

#undef REQUIRE_EXTENSIONS
#tryinclude <websocket>

#if defined _websocket_included
#include <halflife>
#include <sdktools>
#include <tf2_stocks>
#endif

#pragma semicolon 1 //must use semicolon to end lines

#define RED 0
#define BLUE 1
#define TEAM_OFFSET 2
#define DEBUG true

#if defined _websocket_included
#define WEBTV_POSITION_UPDATE_RATE 0.3
#define WEBTV_BUFFER_PROCESS_RATE 0.1
#endif

public Plugin:myinfo =
{
    #if defined _websocket_included
	name = "Livelogs (with SourceTV2D)",
    #else
    name = "Livelogs (no SourceTV2D)",
    #endif
	author = "Prithu \"bladez\" Parker",
	description = "Server-side plugin for the livelogs system. Sends logging request to the livelogs daemon and instigates logging procedures",
	version = "0.1.1",
	url = "http://livelogs.unknown.ip"
};



//------------------------------------------------------------------------------
// Variables
//------------------------------------------------------------------------------

new bool:t_state[2] = { false, false }; //Holds ready state for both teams
new bool:live_at_restart = false;
new bool:is_logging = false;
new String:log_unique_ident[64];

new String:server_ip[64];
new server_port;
new String:ll_listener_address[128];

//Handles for convars
new Handle:livelogs_daemon_address = INVALID_HANDLE; //ip/dns of livelogs daemon
new Handle:livelogs_daemon_port = INVALID_HANDLE; //port of livelogs daemon
new Handle:livelogs_daemon_apikey = INVALID_HANDLE; //the key that must be specified when communicating with the ll daemon

//if websocket is included, let's define the websocket stuff!
#if defined _websocket_included
new webtv_round_time;
new bool:webtv_library_present = false;
new Float:webtv_delay;

new WebsocketHandle:livelogs_webtv_listen_socket = INVALID_WEBSOCKET_HANDLE;
new Handle:livelogs_webtv_listenport = INVALID_HANDLE;
new Handle:livelogs_webtv_children;
new Handle:livelogs_webtv_children_ip;
new Handle:livelogs_webtv_positions_timer = INVALID_HANDLE;

new Handle:livelogs_webtv_buffer = INVALID_HANDLE; //buffer all data, to be sent on a delay equal to that of tv_delay
new Handle:livelogs_webtv_buffer_timer = INVALID_HANDLE; //timer to process the buffer every WEBTV_UPDATE_RATE seconds, only sends events that have time >= tv_delay
#endif

//------------------------------------------------------------------------------
// Startup
//------------------------------------------------------------------------------

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

    //Convars
    livelogs_daemon_address = CreateConVar("livelogs_address", "192.168.35.128", "IP or hostname of the livelogs daemon", FCVAR_PROTECTED);
    livelogs_daemon_port = CreateConVar("livelogs_port", "61222", "Port of the livelogs daemon", FCVAR_PROTECTED);
    livelogs_daemon_apikey = CreateConVar("livelogs_api_key", "123test", "API key for livelogs daemon", FCVAR_PROTECTED|FCVAR_DONTRECORD|FCVAR_UNLOGGED);

    //Setup variables for later sending
    //GetConVarString(FindConVar("ip"), server_ip, sizeof(server_ip));
    
    //we should get the IP via hostip, because sometimes people don't set "ip"
    new longip = GetConVarInt(FindConVar("hostip")), ip_quad[4];
    ip_quad[0] = (longip >> 24) & 0x000000FF;
    ip_quad[1] = (longip >> 16) & 0x000000FF;
    ip_quad[2] = (longip >> 8) & 0x000000FF;
    ip_quad[3] = (longip) & 0x000000FF;
    
    Format(server_ip, sizeof(server_ip), "%d.%d.%d.%d", ip_quad[0], ip_quad[1], ip_quad[2], ip_quad[3]);
    
    server_port = GetConVarInt(FindConVar("hostport"));
    
#if defined _websocket_included
    decl String:tmp[12];
    Format(tmp, sizeof(tmp), "%d", server_port + 2);
    
    livelogs_webtv_listenport = CreateConVar("livelogs_webtv_port", tmp, "The port to listen on for SourceTV 2D connections", FCVAR_PROTECTED);

    livelogs_webtv_children = CreateArray();
    livelogs_webtv_children_ip = CreateArray(ByteCountToCells(33));
    livelogs_webtv_buffer = CreateArray(4096);
    
    
    //add event hooks and shiz for websocket, self explanatory names and event hooks
    HookEvent("player_team", playerTeamChangeEvent);
    HookEvent("player_death", playerDeathEvent);
    HookEvent("player_spawn", playerSpawnEvent);
    HookEvent("player_changeclass", playerClassChangeEvent);
    HookEvent("player_chargedeployed", playerUberEvent);
    HookEvent("teamplay_flag_event", playerFlagEvent);
    HookEvent("teamplay_round_start", roundStartEvent);
    HookEvent("teamplay_round_win", roundEndEvent);
    
    //hook tv_delay so we can adjust the delay dynamically
    HookConVarChange(FindConVar("tv_delay"), delayChangeHook);
#endif
}

#if defined _websocket_included
public OnAllPluginsLoaded()
{
    if (LibraryExists("websocket"))
    {
        webtv_library_present = true;
        /*if (livelogs_webtv_listen_socket == INVALID_WEBSOCKET_HANDLE)
        {
            new webtv_lport = GetConVarInt(livelogs_webtv_listenport);
            
            if (DEBUG) { LogMessage("websocket is present. initialising socket. Address: %s:%d", server_ip, webtv_lport); }
            
            livelogs_webtv_listen_socket = Websocket_Open(server_ip, webtv_lport, onWebSocketConnection, onWebSocketListenError, onWebSocketListenClose);
        }
        */
    }
}

#endif

public OnMapStart()
{
	clearVars();
    
#if defined _websocket_included
    new num_web_clients = GetArraySize(livelogs_webtv_children);
    if (num_web_clients == 0)
        return;
        
    decl String:buffer[64];
    GetCurrentMap(buffer, sizeof(buffer));
    
    Format(buffer, sizeof(buffer), "M%s", buffer);
    
    sendToAllWebChildren(buffer);
#endif
}

//------------------------------------------------------------------------------
// Callbacks
//------------------------------------------------------------------------------

public tournamentStateChangeEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    new client_team = GetClientTeam(GetEventInt(event, "userid")) - TEAM_OFFSET;
    new bool:r_state = GetEventBool(event, "readystate");

    new bool:is_name_change = GetEventBool(event, "namechange");
    if (!is_name_change)
    {
        t_state[client_team] = r_state;

        //we're ready to begin logging at round restart if both teams are ready
        if (t_state[RED] && t_state[BLUE])
        {
            live_at_restart = true;
        }
        else
        {
            live_at_restart = false;
        }
    }
}

public gameRestartEvent(Handle:event, const String:name[], bool:dontBroadcast)
{
    //if teams are ready, get log listener address
    if (live_at_restart)
    {
        requestListenerAddress();
        live_at_restart = false;
        t_state[RED] = false;
        t_state[BLUE] = false;

        is_logging = true;
    }
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

#if defined _websocket_included
public delayChangeHook(Handle:cvar, const String:oldval[], const String:newval[])
{
    LogMessage("delay changed. old: %s new: %s", oldval, newval);
    
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

public OnClientDisconnect(client)
{
    if (IsClientInGame(client))
    {
        decl String:buffer[12];
        Format(buffer, sizeof(buffer), "D%d", GetClientUserId(client));
        
        addToWebBuffer(buffer);
    }
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
    Format(buffer, sizeof(buffer), "S:%d:%d", userid, pclass);
    
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
        
    decl String:map[64], String:game[32], String:buffer[196], String:hostname[128];
    
    GetCurrentMap(map, sizeof(map));
    GetGameFolderName(game, sizeof(game));
    
    GetConVarString(FindConVar("hostname"), hostname, sizeof(hostname));
    
    //IGAME:MAP:TEAM2NAME:TEAM3NAME:HOSTNAME
    Format(buffer, sizeof(buffer), "I%s:%s:%s:%s:%s", game, map, "RED", "BLUE", hostname);
    
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
        livelogs_webtv_positions_timer = CreateTimer(WEBTV_POSITION_UPDATE_RATE, updatePlayerPositionTimer, _, TIMER_REPEAT);
        
    return;
}

public Action:updatePlayerPositionTimer(Handle:timer, any:data)
{
    new num_web_clients = GetArraySize(livelogs_webtv_children);
    if (num_web_clients == 0)
        return Plugin_Continue;
 
    //LogMessage("update player pos");
 
    decl String:buffer[4096];
    
    Format(buffer, sizeof(buffer), "O");
    
    new Float:p_origin[3], Float:p_angle[3]; //two vectors, one containing the position of the player and the other the angle the player is facing
    
    for (new i = 1; i <= MaxClients; i++)
    {
        if (IsClientInGame(i) && IsPlayerAlive(i))
        {
            if (strlen(buffer) > 1) //if more than just "O" is in the buffer, add separator
                Format(buffer, sizeof(buffer), "%s|", buffer); //player positions will be appended after an |
                
            GetClientAbsOrigin(i, p_origin);
            GetClientEyeAngles(i, p_angle);
            
            //we only need X and Y co-ords, and only need theta (angle corresponding to the X Y plane)
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
    
    new iBufferSize = GetArraySize(livelogs_webtv_buffer), num_web_clients = GetArraySize(livelogs_webtv_children);
    
    decl String:buf_split_array[3][4096], String:strbuf[4096];
    
    for (new i = 0; i < iBufferSize; i++)
    {
        //contains strings like timestamp%O3:blah:blah:blah
        GetArrayString(livelogs_webtv_buffer, i, strbuf, sizeof(strbuf)); //string with timestamp%buffer
        
        //if (DEBUG) { LogMessage("Processing buffer. Buf string: %s @ idx %d", strbuf, i); }
        
        ExplodeString(strbuf, "@", buf_split_array, 3, 4096); //now we have the timestamp and buffered data split
        
        //compare timestamps to see if tv_delay has passed
        timediff = current_time - StringToFloat(buf_split_array[0]);
        
        if (timediff > webtv_delay) //i.e. delay seconds has past, time to send data
        {
            //if (DEBUG) { LogMessage("timestamp is outside of delay range. timediff: %f, sending. send msg: %s", timediff, bufdata); }
            
            if (num_web_clients == 0)
            {
                RemoveFromArray(livelogs_webtv_buffer, i);
                iBufferSize--;
                continue;
            }
            
            sendToAllWebChildren(buf_split_array[1], num_web_clients);
            
            RemoveFromArray(livelogs_webtv_buffer, i);
            i--; //push our i down, because we removed an array element and hence shifted the index by << 1
            iBufferSize--; //also move the buffer back 1 to prevent an infinite loop
        }
        else {
        //our timestamp is beyond the delay. therefore, everything following it will be as well
            return Plugin_Continue;
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
        KillTimer(livelogs_webtv_positions_timer);
        livelogs_webtv_positions_timer = INVALID_HANDLE;
    }
}
#endif

//------------------------------------------------------------------------------
// Clean up
//------------------------------------------------------------------------------

public OnMapEnd()
{
	endLogging();
    
/*#if defined _websocket_included
    if (livelogs_webtv_listen_socket != INVALID_WEBSOCKET_HANDLE)
    {
        Websocket_Close(livelogs_webtv_listen_socket);
    }
#endif*/
}

#if defined _websocket_included
public onWebSocketListenClose(WebsocketHandle:listen_sock)
{
    if (DEBUG) { LogMessage("listen sock close"); }
    livelogs_webtv_listen_socket = INVALID_WEBSOCKET_HANDLE;
    
    /*new num_web_clients = GetArraySize(livelogs_webtv_children)
    if (num_web_clients == 0)
        return;
        
    new WebsocketHandle:child_sock;
    
    for (new i = 0; i < num_web_clients; i++)
    {
        child_sock = GetArrayCell(livelogs_webtv_children, i);
        
        Websocket_Close(child_sock);
        
        RemoveFromArray(livelogs_webtv_children, i);
        RemoveFromArray(livelogs_webtv_children_ip, i);
    }*/
    
    KillTimer(livelogs_webtv_positions_timer);
    KillTimer(livelogs_webtv_buffer_timer);
    //ClearArray(livelogs_webtv_children);
    //ClearArray(livelogs_webtv_children_ip);
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
        KillTimer(livelogs_webtv_positions_timer);
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

    GetConVarString(livelogs_daemon_apikey, ll_api_key, sizeof(ll_api_key));

    decl String:split_buffer[5][64];
    new response_len = ExplodeString(rcvd, "!", split_buffer, 6, 64);
    
    //LogMessage("Num Toks: %d Tokenized params: 1 %s 2 %s 3 %s 4 %s 5 %s", response_len, split_buffer[0], split_buffer[1], split_buffer[2], split_buffer[3], split_buffer[4]);
    
    if (response_len == 5)
    {
        if (DEBUG) { LogMessage("Have tokenized response with len > 1. APIKEY: %s, SPECIFIED: %s", ll_api_key, split_buffer[1]); }

        if ((StrEqual("LIVELOG", split_buffer[0])) && (StrEqual(ll_api_key, split_buffer[1])))
        {            
            Format(ll_listener_address, sizeof(ll_listener_address), "%s:%s", split_buffer[2], split_buffer[3]);
            
            if (!StrEqual(split_buffer[4], "REUSE"))
            {
                if (DEBUG) { LogMessage("LL LOG_UNIQUE_IDENT: %s", split_buffer[4]); }
                strcopy(log_unique_ident, sizeof(log_unique_ident), split_buffer[4]);
            }
            
            ServerCommand("logaddress_add %s", ll_listener_address);
            if (DEBUG) { LogMessage("Added address %s to logaddress list", ll_listener_address); }
            
            //now open websocket too
            if ((livelogs_webtv_listen_socket == INVALID_WEBSOCKET_HANDLE) && (webtv_library_present))
            {
                webtv_delay = GetConVarFloat(FindConVar("tv_delay"));
                new webtv_lport = GetConVarInt(livelogs_webtv_listenport);
                if (DEBUG) { LogMessage("websocket is present. initialising socket. Address: %s:%d", server_ip, webtv_lport); }
            
                livelogs_webtv_listen_socket = Websocket_Open(server_ip, webtv_lport, onWebSocketConnection, onWebSocketListenError, onWebSocketListenClose);
            }
        }
    }
    
    CloseHandle(socket);
}

public onSocketDisconnect(Handle:socket, any:arg)
{
	CloseHandle(socket);
	if (DEBUG) { LogMessage("Socket disconnected and closed"); }
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

    if (DEBUG) { LogMessage("Attempting to connect to %s:%d (DATA: %s)", ll_ip, ll_port, msg); }
}

//Command for testing socket sending
public Action:Test_SockSend(client, args)
{
	requestListenerAddress();
}

//------------------------------------------------------------------------------
// Private functions
//------------------------------------------------------------------------------

clearVars()
{
    is_logging = false;
    live_at_restart = false;

    t_state[RED] = false;
    t_state[BLUE] = false;
}

requestListenerAddress()
{
    //SEND STRUCTURE: LIVELOG!123test!192.168.35.1!27015!cp_granary!John
    decl String:ll_request[128], String:ll_api_key[64], String:map[64], String:log_name[64];
    
    GetCurrentMap(map, sizeof(map));
    
    new Handle:ipgn_booker_handle = ConVarExists("mr_ipgnbooker");
    
    if (ipgn_booker_handle != INVALID_HANDLE)
    {
        GetConVarString(ipgn_booker_handle, log_name, sizeof(log_name));
    }
    else
    {
        Format(log_name, sizeof(log_name), "default");
    }
    GetConVarString(livelogs_daemon_apikey, ll_api_key, sizeof(ll_api_key));
    #if defined _websocket_included
    new webtv_port = GetConVarInt(livelogs_webtv_listenport);
    Format(ll_request, sizeof(ll_request), "LIVELOG!%s!%s!%d!%s!%s!%d", ll_api_key, server_ip, server_port, map, log_name, webtv_port);  
    #else
    Format(ll_request, sizeof(ll_request), "LIVELOG!%s!%s!%d!%s!%s", ll_api_key, server_ip, server_port, map, log_name);
    #endif
    sendSocketData(ll_request);
}

endLogging()
{
    if (is_logging)
    {
        is_logging = false;

        ServerCommand("logaddress_del %s", ll_listener_address);
    }
    
    #if defined _websocket_included
    if ((webtv_library_present) && (livelogs_webtv_listen_socket != INVALID_WEBSOCKET_HANDLE))
    {
        CreateTimer(GetConVarFloat(FindConVar("tv_delay")) + 10.0, cleanUpWebSocket);
    }
    #endif
}

stock _:ConVarExists(const String:cvar_name[])
{
    return FindConVar(cvar_name);
}

#if defined _websocket_included
addToWebBuffer(const String:msg[])
{
    if (strlen(msg) < 1)
        return;
        
    new Float:time = GetEngineTime();
    
    decl String:newbuffer[4096];
    Format(newbuffer, sizeof(newbuffer), "%f@%s", time, msg); //append the timestamp to the msg
    
    new bufindex = PushArrayString(livelogs_webtv_buffer, newbuffer);
    
   // decl String:tmp[4096];
    //GetArrayString(livelogs_webtv_buffer, bufindex, tmp, sizeof(tmp));
    
    //LogMessage("Added %s to send buffer. IN BUFFER: %s, INDEX: %d", newbuffer, tmp, bufindex);
    
    if (livelogs_webtv_buffer_timer == INVALID_HANDLE)
        livelogs_webtv_buffer_timer = CreateTimer(WEBTV_BUFFER_PROCESS_RATE, webtv_bufferProcessTimer, _, TIMER_REPEAT);
        
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

public Action:cleanUpWebSocket(Handle:timer, any:data)
{
    Websocket_Close(livelogs_webtv_listen_socket);
}
#endif