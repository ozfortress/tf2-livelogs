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

//------------------------------------------------------------------------------
// STV2D HOOKS, CALLBACKS, FUNCTIONS AND TIMERS
//------------------------------------------------------------------------------

////
//---------------------- EVENT AND CVAR CALLBACKS/HOOKS ----------------------
////

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

////
//---------------------- SOCKET CALLBACKS ----------------------
////

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

////
//---------------------- FUNCTIONS ----------------------
////

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