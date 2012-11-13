/*
    Credit goes to Carbon for basic structure of initiating actions on mp_tournament starts and ends

*/


#include <sourcemod>
#include <socket>

#pragma semicolon 1 //must use semicolon to end lines

#define RED 0
#define BLUE 1
#define TEAM_OFFSET 2
#define DEBUG true

public Plugin:myinfo =
{
	name = "Livelogs",
	author = "Prithu \"bladez\" Parker",
	description = "Server-side plugin for the livelogs system. Sends logging request to the livelogs daemon and instigates logging procedures",
	version = "0.0.1",
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
    GetConVarString(FindConVar("ip"), server_ip, sizeof(server_ip));
    server_port = GetConVarInt(FindConVar("hostport"));
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

public OnMapStart()
{
	clearVars();
}

public OnMapEnd()
{
	endLogging();
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
    if (DEBUG) { LogMessage("Sent data '%s'", msg); }
}

public onSocketReceive(Handle:socket, String:rcvd[], const dataSize, any:arg)
{
    //Livelogs response packet: LIVELOG!api_key!listener_address!listener_port!UNIQUE_IDENT OR REUSE
    LogMessage("Data received: %s", rcvd);

    decl String:ll_api_key[64];

    GetConVarString(livelogs_daemon_apikey, ll_api_key, sizeof(ll_api_key));

    decl String:split_buffer[5][64];
    
    new response_len = ExplodeString(rcvd, "!", split_buffer, sizeof(split_buffer[]), sizeof(split_buffer[][]), true);
    
    if (response_len == 5)
    {
        if ((StrEqual("LIVELOGS", split_buffer[0])) && (StrEqual(ll_api_key, split_buffer[1])))
        {            
            Format(ll_listener_address, sizeof(ll_listener_address), "%s:%d", split_buffer[2], split_buffer[3]);
            
            if (!StrEqual(split_buffer[4], "REUSE"))
            {
                LogMessage("LL LOG_UNIQUE_IDENT: %s", split_buffer[4]);
                strcopy(log_unique_ident, sizeof(log_unique_ident), split_buffer[4]);
            }
            
            ServerCommand("logaddress_add %s", ll_listener_address);
            LogMessage("Added address %s to logaddress list", ll_listener_address);
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
	LogError("Connect socket error %d (errno %d)", errorType, errorNum);
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

    if (DEBUG) { LogMessage("Attempted to open socket"); }
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
        Format(log_name, sizeof(log_name), "unnamed");
    }
    
    GetConVarString(livelogs_daemon_apikey, ll_api_key, sizeof(ll_api_key));
    
    Format(ll_request, sizeof(ll_request), "LIVELOG!%s!%s!%d!%s!%s", ll_api_key, server_ip, server_port, map, log_name);
    
    sendSocketData(ll_request);
}

endLogging()
{
    if (is_logging)
    {
        is_logging = false;

        ServerCommand("logaddress_del %s", ll_listener_address);
    }
}

stock ConVarExists(const String:cvar_name[])
{
    return FindConVar(cvar_name);
}