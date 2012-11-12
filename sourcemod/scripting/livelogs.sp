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

new String:server_port[16];
new String:server_ip[64];
new String:socket_data[256];

//Handles for convars
new Handle:livelogs_daemon_adress = INVALID_HANDLE; //ip/dns of livelogs daemon
new Handle:livelogs_daemon_port = INVALID_HANDLE; //port of livelogs daemon
//new Handle:livelogs_daemon_apikey = INVALID_HANDLE; //the key that must be specified when communicating with the ll daemon

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
    //may just hardcode apikey livelogs_daemon_apikey = CreateConVar("livelogs_api_key", "api123", "API key for livelogs daemon", FCVAR_PROTECTED|FCVAR_DONTRECORD|FCVAR_UNLOGGED);
	
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
		t_state[team] = r_state;

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
	SocketSend(socket, socketData);
	if (DEBUG) { LogMessage("Sent data '%s' to %s:%d", socketData, botIP, botPort); }
	//SocketDisconnect(socket);
}

public onSocketReceive(Handle:socket, String:receiveData[], const dataSize, any:arg)
{
	LogMessage("Data received: %s", receiveData);
	return 0;
}

public onSocketDisconnect(Handle:socket, any:arg)
{
	CloseHandle(socket);
	if (DEBUG) { LogMessage("Socket disconnected and closed"); }
}

public onSocketSendqueueEmpty(Handle:socket, any:arg) 
{
	SocketDisconnect(socket);
	CloseHandle(socket);
	if (DEBUG) { LogMessage("Send queue is empty. Socket closed"); }
}

public onSocketError(Handle:socket, const errorType, const errorNum, any:arg)
{
	LogError("Connect socket error %d (errno %d)", errorType, errorNum);
	CloseHandle(socket);
}

public sendSocketData(String:msg[])
{
	new Handle:socket = SocketCreate(SOCKET_UDP, onSocketError);
	SocketSetSendqueueEmptyCallback(socket,onSocketSendqueueEmpty);
	GetConVarString(ipgn_botip, botIP, sizeof(botIP));
	botPort = GetConVarInt(ipgn_botport);
	Format(socketData, sizeof(socketData), "%s", msg);
	SocketConnect(socket, onSocketConnected, onSocketReceive, onSocketDisconnect, botIP, botPort);
	if (DEBUG) { LogMessage("Attempted to open socket"); }
}

//Command for testing socket sending
public Action:Test_SockSend(client, args)
{
	decl String:tournament[16], String:timestamp[32], String:map[32], String:booker[64], String:tempDemoName[128];

	//give strings values
	GetConVarString(ipgn_tournament, tournament, sizeof(tournament));
	GetConVarString(ipgn_booker, booker, sizeof(booker));
	FormatTime(timestamp, sizeof(timestamp), "%Y%m%d-%H%M");
	GetCurrentMap(map, sizeof(map));
	
	Format(tempDemoName, sizeof(tempDemoName), "%s-%s-%s.dem", booker, timestamp, map);
	if (client == 0)
	{
		CheckForLogFile();
		decl String:msg[192];
		//STOP_RECORD@%s@%s@%s_%s
		Format(msg, sizeof(msg), "STOP_RECORD@%s.%s@%s@%s_%s", tempDemoName, serverPort, log, serverIP, serverPort);
		sendSocketData(msg);
	}
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

}

endLogging()
{
	if (is_logging)
	{
		is_logging = false;
        
        ServerCommand("logaddress_del %s", ll_listener_address);
	}
}