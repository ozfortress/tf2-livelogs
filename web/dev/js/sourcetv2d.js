/*
    Livelogs SourceTV2D Browser client
    
    
    
    
    Credit to Jannik 'Peace-Maker' Hartung @ http://www.wcfan.de/ for the original code
    

*/



var SourceTV2D = {};

function init() {
    "use strict";
    SourceTV2D.socket = null;
    SourceTV2D.canvas = null;
    SourceTV2D.background = null;
    SourceTV2D.ctx = null;
    SourceTV2D.game = null;
    SourceTV2D.map = null;
    SourceTV2D.servername = "";
    SourceTV2D.team = ["Unassigned", "Spectator", "", ""];
    SourceTV2D.teamPoints = [0, 0];
    SourceTV2D.teamPlayerAmount = [0, 0, 0];
    SourceTV2D.teamPlayersAlive = [0, 0];
    SourceTV2D.players = [];
    SourceTV2D.mapsettingsLoaded = false;
    SourceTV2D.mapsettingsFailed = false;
    SourceTV2D.mapsettings = {};
    SourceTV2D.scaling = 1.0;
    SourceTV2D.playerRadius = 5;
    SourceTV2D.width = 0;
    SourceTV2D.height = 0;
    SourceTV2D.timer = null;
    SourceTV2D.roundEnded = -1;
    SourceTV2D.roundEndTime = -1;
    SourceTV2D.roundStartTime = -1;
    SourceTV2D.mp_roundtime = -1;
    SourceTV2D.frags = [];
    SourceTV2D.fragFadeTime = 5;
    SourceTV2D.infos = [];
    SourceTV2D.infosFadeTime = 6;
    SourceTV2D.chat = [];
    SourceTV2D.chatHoldTime = 10;
    SourceTV2D.chatFadeTime = 2;
    SourceTV2D.totalUsersWatching = 0;
    SourceTV2D.shownames = 1;
    $("sourcetv2d").mousemove = null;
    $("#player").html("");
    $("#players2").html("");
    $("#players3").html("");
    $("#players1").html("");
    $("#selectedplayer").html("");
    $("#totalwatching").text("0");
    SourceTV2D.bomb_const = {pickup: 0, dropped: 1, position: 2, planted: 3, defused: 4, exploded: 5, beginplant: 6, abortplant: 7, begindefuse: 8, abortdefuse: 9};
    SourceTV2D.bombDropped = false;
    SourceTV2D.bombPlantTime = -1;
    SourceTV2D.bombPosition = [0, 0];
    SourceTV2D.bombExplodeTime = 45;
    SourceTV2D.bombExploded = false;
    SourceTV2D.bombDefuseTime = -1;
}

$(document).keydown(function (e) {
    "use strict";
    if (($(document.activeElement).attr("id") != "chatinput") && ($(document.activeElement).attr("id") != "chatnick") && (e.which == 32)) {
        SourceTV2D.spacebarPressed = true;
        return false;
    }
});
$(document).keyup(function (e) {
    "use strict";
    if ($(document.activeElement).attr("id") != "chatinput" && $(document.activeElement).attr("id") != "chatnick" && e.which == 32) {
        SourceTV2D.spacebarPressed = false;
        return false;
    }
});

function debug(msg) {
    "use strict";
    $("#debug").html($("#debug").html() + "<br />" + msg);
}

function stv2d_togglenames() {
    "use strict";
    if (SourceTV2D.shownames == 1) {
        SourceTV2D.shownames = 0;
    } else {
        SourceTV2D.shownames = 1;
    }
}

function stv2d_disconnect() {
    "use strict";
    if (SourceTV2D.timer != null) {
        clearInterval(SourceTV2D.timer);
        SourceTV2D.timer = null;
    }
    if (SourceTV2D.ctx != null) {
        SourceTV2D.ctx.font = Math.round(22*SourceTV2D.scaling) + "pt Verdana";
        SourceTV2D.ctx.fillStyle = "rgb(255,255,255)";
        SourceTV2D.ctx.fillText("Disconnected.", 100*SourceTV2D.scaling, 100*SourceTV2D.scaling);
    }
    if (SourceTV2D.socket==null) {
        return;
    }
    
    SourceTV2D.totalUsersWatching -= 1;
    $("#totalwatching").text(SourceTV2D.totalUsersWatching);
    debug("Disconnecting from socket");
    SourceTV2D.socket.close(1000);
    SourceTV2D.socket=null;
}

function stv2d_connect(ip, port) {
    stv2d_disconnect();
    if (SourceTV2D.canvas != null)
    {
        $(SourceTV2D.canvas).remove();
        SourceTV2D.canvas = null;
    }
    init();
    $("#debug").html("");
    SourceTV2D.ip = ip;
    SourceTV2D.port = port;
    var host = "ws://" + ip + ":" + port + "/sourcetv2d";
    try
    {
        // FF needs the Moz prefix..
        if (!window.WebSocket) {
            if (window.MozWebSocket) {
                SourceTV2D.socket = new MozWebSocket(host);
            } else {
                debug("Your browser doesn't support WebSockets.");
                return;
            }
        } else {
            SourceTV2D.socket = new WebSocket(host);
        }
        
        debug("Opening connection to " + ip + ":" +port);
        
        SourceTV2D.socket.onopen = function (msg)
        {
            debug("Connection established");
        };
        
        SourceTV2D.socket.onmessage = function (msg)
        {
            //debug("Received: " + msg.data);
            // I primarily suck at javascript. This may be optimized to read bits instead of whole characters
            var frame = {}, offset = 0;
            frame.type = msg.data.charAt(offset);
            offset += 1;
            debug("Received frame type: " + frame.type + " Msg: " + msg.data);
            switch (frame.type)
            {
                // Initialisation
                case "I":
                {
                    var info = 0;
                    frame.game = "";
                    frame.map = "";
                    frame.team1 = "";
                    frame.team2 = "";
                    frame.hostname = "";
                    for(; offset < msg.data.length; offset++)
                    {
                        if (msg.data.charAt(offset) == ':')
                        {
                            info++;
                            continue;
                        }
                        if (info == 0)
                            frame.game += msg.data.charAt(offset);
                        else if (info == 1)
                            frame.map += msg.data.charAt(offset);
                        else if (info == 2)
                            frame.team1 += msg.data.charAt(offset);
                        else if (info == 3)
                            frame.team2 += msg.data.charAt(offset);
                        else
                            frame.hostname += msg.data.charAt(offset);
                    }
                    debug("Game: " + frame.game);
                    debug("Map: " + frame.map);
                    debug("Team 2: " + frame.team1);
                    debug("Team 3: " + frame.team2);
                    
                    SourceTV2D.game = frame.game;
                    SourceTV2D.map = frame.map;
                    SourceTV2D.servername = frame.hostname;
                    SourceTV2D.team[2] = frame.team1;
                    SourceTV2D.team[3] = frame.team2;
                    $("#teamname2").text(frame.team1);
                    $("#teamname3").text(frame.team2);
                    
                    loadMapImageInfo(frame.game, frame.map);
                    
                    SourceTV2D.timer = setInterval("drawMap()", 50);
                    
                    SourceTV2D.totalUsersWatching++;
                    $("#totalwatching").text(SourceTV2D.totalUsersWatching);
                    break;
                }
                // Map changed
                case "M":
                {
                    frame.map = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        frame.map += msg.data.charAt(offset);
                    }
                    
                    if (SourceTV2D.canvas != null)
                    {
                        $(SourceTV2D.canvas).remove();
                        SourceTV2D.canvas = null;
                    }
                    SourceTV2D.map = frame.map;
                    SourceTV2D.background = null;
                    SourceTV2D.mapsettingsLoaded = false;
                    SourceTV2D.mapsettingsFailed = false;
                    SourceTV2D.teamPoints[0] = SourceTV2D.teamPoints[1] = 0;
                    SourceTV2D.roundEnded = -1;
                    
                    loadMapImageInfo();
                    
                    break;
                }
                // Player connected.
                case "C":
                {
                    var info = 0;
                    frame.userid = "";
                    frame.ip = "";
                    frame.team = "";
                    frame.alive = "";
                    frame.frags = "";
                    frame.deaths = "";
                    frame.health = "";
                    frame.bomb = "";
                    frame.defuser = "";
                    frame.name = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        if (info < 9 && msg.data.charAt(offset) == ':')
                        {
                            info++;
                            continue;
                        }
                        if (info == 0)
                            frame.userid += msg.data.charAt(offset);
                        else if (info == 1)
                            frame.ip += msg.data.charAt(offset);
                        else if (info == 2)
                            frame.team += msg.data.charAt(offset);
                        else if (info == 3)
                            frame.alive += msg.data.charAt(offset);
                        else if (info == 4)
                            frame.frags += msg.data.charAt(offset);
                        else if (info == 5)
                            frame.deaths += msg.data.charAt(offset);
                        else if (info == 6)
                            frame.health += msg.data.charAt(offset);
                        else if (info == 7)
                            frame.bomb += msg.data.charAt(offset);
                        else if (info == 8)
                            frame.defuser += msg.data.charAt(offset);
                        else
                            frame.name += msg.data.charAt(offset);
                    }
                    
                    frame.team = parseInt(frame.team);
                    frame.bomb = parseInt(frame.bomb);
                    frame.defuser = parseInt(frame.defuser);
                    
                    if (frame.team < 2)
                        SourceTV2D.teamPlayerAmount[0]++;
                    else
                    {
                        SourceTV2D.teamPlayerAmount[frame.team-1]++;
                        SourceTV2D.teamPlayersAlive[frame.team-2]++;
                    }
                    
                    frame.alive = parseInt(frame.alive);
                    frame.health = parseInt(frame.health);
                    if (frame.health > 100)
                        frame.health = 100;
                    
                    // On real new connect, it's always "x". If we just connected to the server and we retrieve the player list, it's set to the correct k/d.
                    var frags = 0;
                    if (frame.frags != "x")  
                        frags = parseInt(frame.frags);
                    var deaths = 0;
                    if (frame.deaths != "x")  
                        deaths = parseInt(frame.deaths);
                    
                    var idx = SourceTV2D.players.length;
                    var d = new Date();
                    SourceTV2D.players[idx] = {'userid': parseInt(frame.userid), 'ip': frame.ip, 'name': frame.name, 'team': frame.team, 'positions': [], 'alive': (frame.alive==1), 'health': frame.health, 'hovered': false, 'selected': false, 'frags': frags, 'deaths': deaths, 'got_the_bomb': (frame.bomb==1), 'got_defuser': (frame.defuser==1), 'plant_start_time': -1, 'defuse_start_time': -1};
                    // Only show the connect message, if he's newly joined -> no team yet.
                    if (SourceTV2D.players[idx].team == 0)
                        SourceTV2D.infos[SourceTV2D.infos.length] = {'msg': frame.name + " has joined the server", 'time': d.getTime()/1000};
                    
                    var playerList = $("#players" + (SourceTV2D.players[idx].team==0?1:SourceTV2D.players[idx].team));
                    playerList.html(playerList.html() + "<div class=\"player\" id=\"usrid_" + SourceTV2D.players[idx].userid + "\" onclick=\"selectPlayer(" + SourceTV2D.players[idx].userid + ");\" onmouseover=\"highlightPlayer(" + SourceTV2D.players[idx].userid + ");\" onmouseout=\"unhighlightPlayer(" + SourceTV2D.players[idx].userid + ");\">" + SourceTV2D.players[idx].name + "</div>");
                    
                    sortScoreBoard();
                    
                    //if (window.console && window.console.log)
                    //    window.console.log("Player connected: #" + SourceTV2D.players[idx].userid + ": " + SourceTV2D.players[idx].name);
                    break;
                }
                // Player disconnected
                case "D":
                {
                    frame.userid = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        frame.userid += msg.data.charAt(offset);
                    }
                    frame.userid = parseInt(frame.userid);
                    //debug("Player disconnected: #" + frame.userid);
                    
                    var d = new Date();
                    for(var i=0;i<SourceTV2D.players.length;i++)
                    {
                        if (SourceTV2D.players[i].userid == frame.userid)
                        {
                            if (SourceTV2D.players[i].team < 2)
                                SourceTV2D.teamPlayerAmount[0]--;
                            else
                            {
                                SourceTV2D.teamPlayerAmount[SourceTV2D.players[i].team-1]--;
                                if (SourceTV2D.players[i].alive)
                                    SourceTV2D.teamPlayersAlive[SourceTV2D.players[i].team-2]--;
                            }
                            SourceTV2D.infos[SourceTV2D.infos.length] = {'msg': SourceTV2D.players[i].name + " has left the server", 'time': d.getTime()/1000};
                            // Handle our player list
                            $("#usrid_" + frame.userid).remove();
                            if (SourceTV2D.players[i].selected)
                                $("#selectedplayer").html("");
                            SourceTV2D.players.splice(i, 1);
                            break;
                        }
                    }
                    sortScoreBoard();
                    //if (window.console && window.console.log)
                    //    window.console.log("Player disconnected: #" + frame.userid);
                    break;
                }
                // Player changed team
                case "T":
                {
                    var info = 0;
                    frame.userid = "";
                    frame.team = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        if (msg.data.charAt(offset) == ':')
                        {
                            info++;
                            continue;
                        }
                        if (info == 0)
                            frame.userid += msg.data.charAt(offset);
                        else
                            frame.team += msg.data.charAt(offset);
                    }
                    frame.userid = parseInt(frame.userid);
                    frame.team = parseInt(frame.team);
                    
                    var idx = -1;
                    for(var i=0;i<SourceTV2D.players.length;i++)
                    {
                        if (SourceTV2D.players[i].userid == frame.userid)
                        {
                            idx = i;
                            break;
                        }
                    }
                    if (idx != -1)
                    {
                        // He joined that team
                        if (frame.team < 2)
                            SourceTV2D.teamPlayerAmount[0]++;
                        else
                        {
                            SourceTV2D.teamPlayerAmount[frame.team-1]++;
                            if (SourceTV2D.players[idx].alive)
                                SourceTV2D.teamPlayersAlive[frame.team-2]++;
                        }
                        // He left that team
                        if (SourceTV2D.players[idx].team < 2)
                            SourceTV2D.teamPlayerAmount[0]--;
                        else
                        {
                            SourceTV2D.teamPlayerAmount[SourceTV2D.players[idx].team-1]--;
                            if (SourceTV2D.players[idx].alive)
                                SourceTV2D.teamPlayersAlive[SourceTV2D.players[idx].team-2]--;
                        }
                        
                        // Handle our player list
                        $("#players" + (frame.team==0?1:frame.team)).append($("#usrid_" + frame.userid));
                        
                        var d = new Date();
                        SourceTV2D.players[idx].team = frame.team;
                        SourceTV2D.infos[SourceTV2D.infos.length] = {'msg': SourceTV2D.players[idx].name + " changed team to " + SourceTV2D.team[SourceTV2D.players[idx].team], 'time': d.getTime()/1000};
                        
                        if (SourceTV2D.players[idx].team < 2)
                            SourceTV2D.players[idx].positions.clear();
                        
                        //debug("Player #" + frame.userid + " changed team to: " + SourceTV2D.players[idx].team);
                        sortScoreBoard();
                    }
                    else
                        debug("NOT FOUND!!! Player #" + frame.userid + " changed team to: " + frame.team);
                    break;
                }
                // Players origin updated
                case "O":
                {
                    if (!SourceTV2D.mapsettingsLoaded || SourceTV2D.background == null)
                        break;
                    
                    var info = 0;
                    var playerIndex = 0;
                    frame.positions = [];
                    for(; offset<msg.data.length; offset++)
                    {
                        // next player
                        if (msg.data.charAt(offset) == '|')
                        {
                            info = 0;
                            playerIndex++;
                            continue;
                        }
                        
                        if (msg.data.charAt(offset) == ':')
                        {
                            info++;
                            continue;
                        }
                        if (frame.positions[playerIndex] == undefined)
                            frame.positions[playerIndex] = new Array('','','','','');
                        
                        frame.positions[playerIndex][info] += msg.data.charAt(offset);
                    }
                    
                    // Save the player positions
                    var idx = -1;
                    var d = new Date();
                    var time = d.getTime();
                    for(var i=0;i<frame.positions.length;i++)
                    {
                        frame.positions[i][0] = parseInt(frame.positions[i][0]);
                        frame.positions[i][1] = parseInt(frame.positions[i][1]);
                        frame.positions[i][2] = parseInt(frame.positions[i][2]);
                        frame.positions[i][3] = parseInt(frame.positions[i][3]);
                        
                        frame.positions[i][3] += 90;
                        
                        if (frame.positions[i][3] < 0)
                            frame.positions[i][3] *= -1;
                        else if (frame.positions[i][3] > 0)
                            frame.positions[i][3] = 360-frame.positions[i][3];
                        
                        frame.positions[i][3] = (Math.PI/180)*frame.positions[i][3];
                        
                        //frame.positions[i][4] = parseInt(frame.positions[i][4]);
                        if (SourceTV2D.mapsettings.flipx)
                            frame.positions[i][1] *= -1;
                        if (SourceTV2D.mapsettings.flipy)
                            frame.positions[i][2] *= -1;
                        
                        frame.positions[i][1] = Math.round(((frame.positions[i][1] + SourceTV2D.mapsettings.xoffset) / SourceTV2D.mapsettings.scale)); //* SourceTV2D.scaling);
                        frame.positions[i][2] = Math.round(((frame.positions[i][2] + SourceTV2D.mapsettings.yoffset) / SourceTV2D.mapsettings.scale)); //* SourceTV2D.scaling);
                        
                        debug("CANVAS X: " + frame.positions[i][1] + ", CANVAS Y: " + frame.positions[i][2]);
                        
                        // Get the correct team color
                        idx = -1;
                        for(var p=0;p<SourceTV2D.players.length;p++)
                        {
                            if (SourceTV2D.players[p].userid == frame.positions[i][0])
                            {
                                idx = p;
                                break;
                            }
                        }
                        
                        if (idx != -1)
                        {
                            SourceTV2D.players[idx].positions[SourceTV2D.players[idx].positions.length] = {'x': frame.positions[i][1], 'y': frame.positions[i][2], 'angle': frame.positions[i][3], 'time': time, 'diffx': null, 'diffy': null, 'swapx': null, 'swapy': null, 'diedhere': false, 'hurt': false};
                        }
                        
                        //debug("Player moved: #" + frame.positions[i][0] + " - x: " + frame.positions[i][1] + ", y: " + frame.positions[i][2] + ", angle: " + frame.positions[i][3]);
                    }
                    
                    break;
                }
                // Round start
                case "R":
                {
                    frame.roundstart = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        frame.roundstart += msg.data.charAt(offset);
                    }
                    SourceTV2D.roundEnded = -1;
                    SourceTV2D.roundEndTime = -1;
                    SourceTV2D.roundStartTime = parseInt(frame.roundstart);
                    
                    SourceTV2D.bombPlantTime = -1;
                    SourceTV2D.bombExploded = false;
                    SourceTV2D.bombDefuseTime = -1;
                    
                    break;
                }
                // Round end
                case "E":
                {
                    frame.winnerteam = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        frame.winnerteam += msg.data.charAt(offset);
                    }
                    
                    frame.winnerteam = parseInt(frame.winnerteam);
                    
                    SourceTV2D.teamPoints[frame.winnerteam-2]++;
                    SourceTV2D.roundEnded = frame.winnerteam;
                    
                    var d = new Date();
                    SourceTV2D.roundEndTime = Math.floor(d.getTime()/1000);
                    
                    SourceTV2D.bombDropped = false;
                    
                    break;
                }
                // ConVar changed
                case "V":
                {
                    if (SourceTV2D.game == "cstrike")
                    {
                        var info = 0;
                        frame.roundtime = "";
                        frame.c4timer = "";
                        for(; offset<msg.data.length; offset++)
                        {
                            if (msg.data.charAt(offset) == ':')
                            {
                                info++;
                                continue;
                            }
                            
                            if (info == 0)
                              frame.roundtime += msg.data.charAt(offset);
                            else
                              frame.c4timer += msg.data.charAt(offset);
                        }
                        
                        frame.roundtime = parseFloat(frame.roundtime);
                        frame.c4timer = parseFloat(frame.c4timer);
                        SourceTV2D.mp_roundtime = Math.ceil(frame.roundtime*60.0);
                        SourceTV2D.bombExplodeTime = frame.c4timer;
                    }
                    
                    break;
                }
                // Someone killed somebody
                case "K":
                {
                    if (SourceTV2D.ctx == null)
                        break;
                    
                    var info = 0;
                    frame.victim = "";
                    frame.attacker = "";
                    frame.weapon = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        if (info < 2 && msg.data.charAt(offset) == ':')
                        {
                            info++;
                            continue;
                        }
                        if (info == 0)
                            frame.victim += msg.data.charAt(offset);
                        else if (info == 1)
                            frame.attacker += msg.data.charAt(offset);
                        else
                            frame.weapon += msg.data.charAt(offset);
                    }
                    
                    frame.attacker = parseInt(frame.attacker);
                    frame.victim = parseInt(frame.victim);
                    
                    var idxV = -1;
                    var idxA = -1;
                    for(var i=0;i<SourceTV2D.players.length;i++)
                    {
                        if (SourceTV2D.players[i].userid == frame.attacker)
                        {
                            idxA = i;
                        }
                        if (SourceTV2D.players[i].userid == frame.victim)
                        {
                            idxV = i;
                        }
                    }
                    
                    var attackername = "";
                    var attackerteam = 0;
                    if (frame.attacker == 0)
                        attackername = "WORLD";
                    else if (idxA == -1)
                        attackername = "NotFound(#" + frame.attacker + ")";
                    else
                    {
                        SourceTV2D.players[idxA].frags++;
                        attackername = SourceTV2D.players[idxA].name;
                        attackerteam = SourceTV2D.players[idxA].team;
                    }
                    
                    var victimname = "";
                    var victimteam = 0;
                    if (idxV == -1)
                        victimname = "NotFound(#" + frame.victim + ")";
                    else
                    {
                        victimname = SourceTV2D.players[idxV].name;
                        victimteam = SourceTV2D.players[idxV].team;
                        SourceTV2D.players[idxV].alive = false;
                        SourceTV2D.players[idxV].got_defuser = false;
                        SourceTV2D.players[idxV].deaths++;
                        SourceTV2D.teamPlayersAlive[SourceTV2D.players[idxV].team-2]--;
                        if (SourceTV2D.players[idxV].positions.length != 0)
                        {
                            SourceTV2D.players[idxV].positions[SourceTV2D.players[idxV].positions.length-1].diedhere = true;
                        }
                    }
                    
                    // Suicides = frags-1
                    if (idxV != -1 && idxA != -1 && idxV == idxA)
                    {
                        // We added one frag already above..
                        SourceTV2D.players[idxV].frags-=2;
                    }
                    
                    var d = new Date();
                    SourceTV2D.frags[SourceTV2D.frags.length] = {'attacker': attackername, 'ateam': attackerteam, 'victim': victimname, 'vteam': victimteam, 'weapon': frame.weapon, 'time': (d.getTime()/1000)};
                    
                    sortScoreBoard();
                    
                    //debug("Player " + attackername + " killed " + victimname + " with " + frame.weapon);
                    break;
                }
                // Player spawned
                case "S":
                {
                    frame.userid = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        frame.userid += msg.data.charAt(offset);
                    }
                    frame.userid = parseInt(frame.userid);
                    
                    var idx = -1;
                    for(var i=0;i<SourceTV2D.players.length;i++)
                    {
                        if (SourceTV2D.players[i].userid == frame.userid)
                        {
                            idx = i;
                            break;
                        }
                    }
                    if (idx != -1)
                    {
                        if (!SourceTV2D.players[idx].alive)
                            SourceTV2D.teamPlayersAlive[SourceTV2D.players[idx].team-2]++;
                        SourceTV2D.players[idx].alive = true;
                        SourceTV2D.players[idx].health = 100;
                        SourceTV2D.players[idx].plant_start_time = -1;
                        SourceTV2D.players[idx].defuse_start_time = -1;
                    }
                    break;
                }
                // Player said something
                case "X":
                {
                    var info = 0;
                    frame.userid = "";
                    frame.msg = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        if (info == 0 && msg.data.charAt(offset) == ':')
                        {
                            info++;
                            continue;
                        }
                        if (info == 0)
                            frame.userid += msg.data.charAt(offset);
                        else
                            frame.msg += msg.data.charAt(offset);
                    }
                    frame.userid = parseInt(frame.userid);
                    
                    // Console?
                    if (frame.userid == 0)
                    {
                        var d = new Date();
                        SourceTV2D.chat[SourceTV2D.chat.length] = {'name': "Console", 'team': 0, 'msg': frame.msg, 'time': d.getTime()/1000};
                        break;
                    }
                    
                    var idx = -1;
                    for(var i=0;i<SourceTV2D.players.length;i++)
                    {
                        if (SourceTV2D.players[i].userid == frame.userid)
                        {
                            idx = i;
                            break;
                        }
                    }
                    if (idx != -1)
                    {
                        var d = new Date();
                        SourceTV2D.chat[SourceTV2D.chat.length] = {'name': SourceTV2D.players[idx].name, 'team': SourceTV2D.players[idx].team, 'msg': frame.msg, 'time': d.getTime()/1000};
                    }
                    //debug("Player #" + frame.userid + " said: " + frame.msg);
                    break;
                }
                // Player was hurt
                case "H":
                {
                    var info = 0;
                    frame.userid = "";
                    frame.dmg = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        if (msg.data.charAt(offset) == ':')
                        {
                            info++;
                            continue;
                        }
                        if (info == 0)
                            frame.userid += msg.data.charAt(offset);
                        else
                            frame.dmg += msg.data.charAt(offset);
                    }
                    frame.userid = parseInt(frame.userid);
                    frame.dmg = parseInt(frame.dmg);
                    
                    var idx = -1;
                    for(var i=0;i<SourceTV2D.players.length;i++)
                    {
                        if (SourceTV2D.players[i].userid == frame.userid)
                        {
                            idx = i;
                            break;
                        }
                    }
                    if (idx != -1)
                    {
                        SourceTV2D.players[idx].health =  SourceTV2D.players[idx].health - frame.dmg;
                        if (SourceTV2D.players[idx].health < 0)
                            SourceTV2D.players[idx].health = 0;
                        if (SourceTV2D.players[idx].positions.length > 0)
                            SourceTV2D.players[idx].positions[SourceTV2D.players[idx].positions.length-1].hurt = true;
                    }
                    break;
                }
                // SourceTV2D Chat message
                case "Z":
                {
                    frame.message = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        frame.message += msg.data.charAt(offset);
                    }
                    var d = new Date();
                    var timestring = "(";
                    if (d.getHours() < 10)
                      timestring += "0";
                    timestring += d.getHours() + ":";
                    if (d.getMinutes() < 10)
                      timestring += "0";
                    timestring += d.getMinutes() + ":";
                    if (d.getSeconds() < 10)
                      timestring += "0";
                    timestring += d.getSeconds() + ") ";
                    
                    $("#chatoutput").append(document.createTextNode(timestring + frame.message));
                    $("#chatoutput").append("<br />");
                    $('#chatoutput').prop('scrollTop', $('#chatoutput').prop('scrollHeight'));
                    
                    break;
                }
                // SourceTV2D spectator amount changed
                case "A":
                {
                    frame.totalwatching = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        frame.totalwatching += msg.data.charAt(offset);
                    }
                    frame.totalwatching = parseInt(frame.totalwatching);
                    SourceTV2D.totalUsersWatching = frame.totalwatching;
                    $("#totalwatching").text(SourceTV2D.totalUsersWatching);
                    
                    break;
                }
                // Player changed his name
                case "N":
                {
                    var info = 0;
                    frame.userid = "";
                    frame.name = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        if (msg.data.charAt(offset) == ':')
                        {
                            info++;
                            continue;
                        }
                        if (info == 0)
                            frame.userid += msg.data.charAt(offset);
                        else
                            frame.name += msg.data.charAt(offset);
                    }
                    frame.userid = parseInt(frame.userid);
                    
                    var idx = -1;
                    for(var i=0;i<SourceTV2D.players.length;i++)
                    {
                        if (SourceTV2D.players[i].userid == frame.userid)
                        {
                            idx = i;
                            break;
                        }
                    }
                    if (idx != -1)
                    {
                        var d = new Date();
                        SourceTV2D.infos[SourceTV2D.infos.length] = {'msg': SourceTV2D.players[idx].name + " changed team to " + frame.name, 'time': d.getTime()/1000};
                        SourceTV2D.players[idx].name = frame.name;
                        $("#usrid_" + frame.userid).text(frame.name);
                    }
                    break;
                }
                // Bomb action
                case "B":
                {
                    var info = 0;
                    frame.action = "";
                    frame.userid = "";
                    frame.posX = "";
                    frame.posY = "";
                    frame.plantTime = "";
                    frame.haskit = "";
                    for(; offset<msg.data.length; offset++)
                    {
                        if (msg.data.charAt(offset) == ':')
                        {
                            info++;
                            continue;
                        }
                        if (info == 0)
                            frame.action += msg.data.charAt(offset);
                        else if (parseInt(frame.action) == SourceTV2D.bomb_const.position || parseInt(frame.action) == SourceTV2D.bomb_const.planted)
                        {
                          if (info == 1)
                            frame.posX += msg.data.charAt(offset);
                          else if (info == 2)
                            frame.posY += msg.data.charAt(offset);
                          else if (parseInt(frame.action) == SourceTV2D.bomb_const.planted)
                          {
                            if (info == 3)
                              frame.plantTime += msg.data.charAt(offset);
                            else
                              frame.userid += msg.data.charAt(offset);
                          }
                        }
                        else if (parseInt(frame.action) == SourceTV2D.bomb_const.begindefuse)
                        {
                          if (info == 1)
                            frame.haskit += msg.data.charAt(offset);
                          else
                            frame.userid += msg.data.charAt(offset);
                        }
                        else if (parseInt(frame.action) != SourceTV2D.bomb_const.exploded)
                            frame.userid += msg.data.charAt(offset);
                    }
                    frame.action = parseInt(frame.action);
                    frame.userid = parseInt(frame.userid);
                    frame.posX = parseInt(frame.posX);
                    frame.posY = parseInt(frame.posY);
                    frame.plantTime = parseInt(frame.plantTime);
                    frame.haskit = parseInt(frame.haskit);
                    
                    if (frame.action != SourceTV2D.bomb_const.position && frame.action != SourceTV2D.bomb_const.exploded)
                    {
                      // Find player with that userid
                      var idx = -1;
                      for(var i=0;i<SourceTV2D.players.length;i++)
                      {
                          if (SourceTV2D.players[i].userid == frame.userid)
                          {
                              idx = i;
                              break;
                          }
                      }
                      if (idx != -1)
                      {
                          if (frame.action == SourceTV2D.bomb_const.pickup)
                          {
                              // Someone else got the bomb. Only one bomb at the time.
                              for(var p=0;p<SourceTV2D.players.length;p++)
                              {
                                  SourceTV2D.players[p].got_the_bomb = false;
                              }
                              SourceTV2D.players[idx].got_the_bomb = true;
                              SourceTV2D.bombDropped = false;
                          }
                          else if (frame.action == SourceTV2D.bomb_const.dropped)
                          {
                              SourceTV2D.players[idx].got_the_bomb = false;
                              SourceTV2D.bombDropped = true;
                          }
                      }
                      
                      if (frame.action == SourceTV2D.bomb_const.planted)
                      {
                        SourceTV2D.bombDropped = false;
                        SourceTV2D.bombDefused = false;
                        
                        SourceTV2D.players[idx].got_the_bomb = false;
                        
                        if (SourceTV2D.mapsettings.flipx)
                            frame.posX *= -1;
                        if (SourceTV2D.mapsettings.flipy)
                            frame.posY *= -1;
                        
                        SourceTV2D.bombPosition[0] = Math.round(((frame.posX + SourceTV2D.mapsettings.xoffset) / SourceTV2D.mapsettings.scale) * SourceTV2D.scaling);
                        SourceTV2D.bombPosition[1] = Math.round(((frame.posY + SourceTV2D.mapsettings.yoffset) / SourceTV2D.mapsettings.scale) * SourceTV2D.scaling);
                        SourceTV2D.bombPlantTime = frame.plantTime;
                        
                        debug("Bomb was planted at x: " + SourceTV2D.bombPosition[0] + ", y: " + SourceTV2D.bombPosition[1] + " at " + SourceTV2D.bombPlantTime);
                        
                        if (idx != -1)
                        {
                          var d = new Date();
                          SourceTV2D.infos[SourceTV2D.infos.length] = {'msg': SourceTV2D.players[idx].name + " planted the bomb!", 'time': d.getTime()/1000};
                        }
                      }
                      else if (frame.action == SourceTV2D.bomb_const.defused)
                      {
                        var d = new Date();
                        SourceTV2D.bombDropped = false;
                        SourceTV2D.bombDefuseTime = d.getTime()/1000;
                        
                        if (idx != -1)
                        {
                          SourceTV2D.infos[SourceTV2D.infos.length] = {'msg': SourceTV2D.players[idx].name + " defused the bomb!", 'time': d.getTime()/1000};
                        }
                      }
                    }
                    else
                    {
                      if (frame.action == SourceTV2D.bomb_const.position)
                      {
                        if (SourceTV2D.mapsettings.flipx)
                            frame.posX *= -1;
                        if (SourceTV2D.mapsettings.flipy)
                            frame.posY *= -1;
                        
                        SourceTV2D.bombPosition[0] = Math.round(((frame.posX + SourceTV2D.mapsettings.xoffset) / SourceTV2D.mapsettings.scale) * SourceTV2D.scaling);
                        SourceTV2D.bombPosition[1] = Math.round(((frame.posY + SourceTV2D.mapsettings.yoffset) / SourceTV2D.mapsettings.scale) * SourceTV2D.scaling);
                        
                        // If the bomb is moving, it's obviously dropped.
                        SourceTV2D.bombDropped = true;
                      }
                      if (frame.action == SourceTV2D.bomb_const.exploded)
                      {
                        SourceTV2D.bombExploded = true;
                        var d = new Date();
                        SourceTV2D.infos[SourceTV2D.infos.length] = {'msg': "The bomb exploded!", 'time': d.getTime()/1000};
                        
                        for(var i=0;i<SourceTV2D.players.length;i++)
                        {
                          SourceTV2D.players[i].defuse_start_time = -1;
                          SourceTV2D.players[i].plant_start_time = -1;
                        }
                      }
                    }
                    break;
                }
            }
        };
        SourceTV2D.socket.onerror = function (msg)
        {
            if (SourceTV2D.ctx != null)
            {
                SourceTV2D.ctx.font = Math.round(22*SourceTV2D.scaling) + "pt Verdana";
                SourceTV2D.ctx.fillStyle = "rgb(255,255,255)";
                SourceTV2D.ctx.fillText("Disconnected.", 100*SourceTV2D.scaling, 100*SourceTV2D.scaling);
            }
            debug("Socket reported error!");
        };
        SourceTV2D.socket.onclose = function (msg)
        {
            if (SourceTV2D.ctx != null)
            {
                SourceTV2D.ctx.font = Math.round(22*SourceTV2D.scaling) + "pt Verdana";
                SourceTV2D.ctx.fillStyle = "rgb(255,255,255)";
                SourceTV2D.ctx.fillText("Disconnected.", 100*SourceTV2D.scaling, 100*SourceTV2D.scaling);
            }
            debug("Disconnected - readyState: " + this.readyState + " Code: " + msg.code + ". Reason:" + msg.reason + " - wasClean: " + msg.wasClean);
        };
    }
    catch(ex) {
        debug('Error: ' + ex);
    }
}

function drawMap() {
    "use strict";
    try
    {
        if (SourceTV2D.ctx == null)
            return;
        // Clear the canvas.
        SourceTV2D.ctx.clearRect(0,0,SourceTV2D.width,SourceTV2D.height);
        if (SourceTV2D.background != null)
            SourceTV2D.ctx.drawImage(SourceTV2D.background,0,0,SourceTV2D.width,SourceTV2D.height);
        else
        {
            SourceTV2D.ctx.save();
            SourceTV2D.ctx.beginPath();
            SourceTV2D.ctx.fillStyle = "rgb(0, 0, 0)";
            SourceTV2D.ctx.rect(0, 0, SourceTV2D.width, SourceTV2D.height);
            SourceTV2D.ctx.fill();
            SourceTV2D.ctx.restore();
        }
        
        // Draw the kill messages
        var d = new Date();
        var time = d.getTime()/1000;
        SourceTV2D.ctx.textAlign = "left";
        SourceTV2D.ctx.font = Math.round(10*SourceTV2D.scaling) + "pt Verdana";
        for(var i=0;i<SourceTV2D.frags.length;i++)
        {
            if ((time - SourceTV2D.frags[i].time) > SourceTV2D.fragFadeTime)
            {
                SourceTV2D.frags.splice(i, 1);
                i--;
                continue;
            }
            
            SourceTV2D.ctx.save();
            
            var alpha = 1.0 - (time - SourceTV2D.frags[i].time) / SourceTV2D.fragFadeTime;
            
            if (SourceTV2D.frags[i].ateam == 2)
                SourceTV2D.ctx.fillStyle = "rgba(255,0,0," + alpha + ")";
            else if (SourceTV2D.frags[i].ateam == 3)
                SourceTV2D.ctx.fillStyle = "rgba(0,0,255," + alpha + ")";
            
            SourceTV2D.ctx.fillText(SourceTV2D.frags[i].attacker, (50*SourceTV2D.scaling), ((50 + (SourceTV2D.frags.length-i-1)*20)*SourceTV2D.scaling));
            
            var offs = SourceTV2D.ctx.measureText(SourceTV2D.frags[i].attacker).width + 10*SourceTV2D.scaling;
            SourceTV2D.ctx.fillStyle = "rgba(255,255,255," + alpha + ")";
            
            SourceTV2D.ctx.fillText(SourceTV2D.frags[i].weapon, (50*SourceTV2D.scaling + offs), ((50 + (SourceTV2D.frags.length-i-1)*20)*SourceTV2D.scaling));
            
            offs += SourceTV2D.ctx.measureText(SourceTV2D.frags[i].weapon).width + 10*SourceTV2D.scaling;
            
            if (SourceTV2D.frags[i].vteam == 2)
                SourceTV2D.ctx.fillStyle = "rgba(255,0,0," + alpha + ")";
            else if (SourceTV2D.frags[i].vteam == 3)
                SourceTV2D.ctx.fillStyle = "rgba(0,0,255," + alpha + ")";
            
            SourceTV2D.ctx.fillText(SourceTV2D.frags[i].victim, (50*SourceTV2D.scaling + offs), ((50 + (SourceTV2D.frags.length-i-1)*20)*SourceTV2D.scaling));
            SourceTV2D.ctx.restore();
        }
        
        
        // Draw the connect/disconnect messages
        SourceTV2D.ctx.font = Math.round(11*SourceTV2D.scaling) + "pt Verdana";
        for(var i=0;i<SourceTV2D.infos.length;i++)
        {
            if ((time - SourceTV2D.infos[i].time) > SourceTV2D.infosFadeTime)
            {
                SourceTV2D.infos.splice(i, 1);
                i--;
                continue;
            }
            
            SourceTV2D.ctx.save();
            var alpha = 1.0 - (time - SourceTV2D.infos[i].time) / SourceTV2D.infosFadeTime;
            SourceTV2D.ctx.fillStyle = "rgba(255,255,255," + alpha + ")";
            
            SourceTV2D.ctx.fillText(SourceTV2D.infos[i].msg, ((SourceTV2D.width-SourceTV2D.ctx.measureText(SourceTV2D.infos[i].msg).width)-50*SourceTV2D.scaling), ((50 + (SourceTV2D.infos.length-i-1)*20)*SourceTV2D.scaling));
            SourceTV2D.ctx.restore();
        }
        
        
        // Draw the chat
        var d = new Date();
        var time = d.getTime()/1000;
        SourceTV2D.ctx.textAlign = "left";
        SourceTV2D.ctx.font = Math.round(12*SourceTV2D.scaling) + "pt Verdana";
        for(var i=(SourceTV2D.chat.length-1);i>=0;i--)
        {
            if ((time - SourceTV2D.chat[i].time) > (SourceTV2D.chatHoldTime + SourceTV2D.chatFadeTime))
            {
                SourceTV2D.chat.splice(i, 1);
                if (SourceTV2D.chat.length > 0)
                    i++;
                continue;
            }
            
            SourceTV2D.ctx.save();
            
            var alpha = 1.0;
            if ((time - SourceTV2D.chat[i].time) > SourceTV2D.chatHoldTime)
                alpha = 1.0 - (time - SourceTV2D.chat[i].time - SourceTV2D.chatHoldTime) / SourceTV2D.chatFadeTime;
            
            if (SourceTV2D.chat[i].team == 0)
                SourceTV2D.ctx.fillStyle = "rgba(255,165,0," + alpha + ")";
            else if (SourceTV2D.chat[i].team == 1)
                SourceTV2D.ctx.fillStyle = "rgba(255,255,255," + alpha + ")";
            else if (SourceTV2D.chat[i].team == 2)
                SourceTV2D.ctx.fillStyle = "rgba(255,0,0," + alpha + ")";
            else if (SourceTV2D.chat[i].team == 3)
                SourceTV2D.ctx.fillStyle = "rgba(0,0,255," + alpha + ")";
            
            SourceTV2D.ctx.fillText(SourceTV2D.chat[i].name, (50*SourceTV2D.scaling), (SourceTV2D.height-(50 + (SourceTV2D.chat.length-i-1)*20)*SourceTV2D.scaling));
            
            var offs = SourceTV2D.ctx.measureText(SourceTV2D.chat[i].name).width;
            SourceTV2D.ctx.fillStyle = "rgba(255,165,0," + alpha + ")";
            
            SourceTV2D.ctx.fillText(": " + SourceTV2D.chat[i].msg, (50*SourceTV2D.scaling + offs), (SourceTV2D.height-(50 + (SourceTV2D.chat.length-i-1)*20)*SourceTV2D.scaling));
            SourceTV2D.ctx.restore();
        }
        
        // Show that notice, if the mapconfig wasn't found
        if (SourceTV2D.background == null || SourceTV2D.mapsettingsFailed)
        {
            SourceTV2D.ctx.save();
            SourceTV2D.ctx.fillStyle = "rgb(255,255,255)";
            SourceTV2D.ctx.font = Math.round(20*SourceTV2D.scaling) + "pt Verdana";
            var text = "No map image.";
            if (SourceTV2D.mapsettingsFailed) {
                text = "Map config failed to load. Player positions can not be shown.";
                SourceTV2D.ctx.fillStyle = "rgb(255,0,0)";
            }
            SourceTV2D.ctx.fillText(text, (SourceTV2D.width - SourceTV2D.ctx.measureText(text).width)/2, (SourceTV2D.height/2));
            SourceTV2D.ctx.restore();
        }
        
        // Draw dropped bomb on map
        if (SourceTV2D.bombDropped)
        {
          SourceTV2D.ctx.save();
          SourceTV2D.ctx.fillStyle = "#FF4500";
          SourceTV2D.ctx.beginPath();
          SourceTV2D.ctx.arc(SourceTV2D.bombPosition[0], SourceTV2D.bombPosition[1], 6*SourceTV2D.scaling, 0, Math.PI*2, true);
          SourceTV2D.ctx.fill();
          
          SourceTV2D.ctx.strokeStyle = "#FFFFFF";
          SourceTV2D.ctx.beginPath();
          SourceTV2D.ctx.arc(SourceTV2D.bombPosition[0], SourceTV2D.bombPosition[1], 6*SourceTV2D.scaling, 0, Math.PI*2, true);
          SourceTV2D.ctx.stroke();
          
          SourceTV2D.ctx.font = Math.round(7*SourceTV2D.scaling) + "pt Verdana";
          SourceTV2D.ctx.fillStyle = "#FFFFFF";
          SourceTV2D.ctx.fillText("B", SourceTV2D.bombPosition[0]-4*SourceTV2D.scaling, SourceTV2D.bombPosition[1] + 3);
          SourceTV2D.ctx.restore();
        }
        
        if (SourceTV2D.bombExploded)
        {
          SourceTV2D.ctx.save();
          SourceTV2D.ctx.fillStyle = "#FF8C00";
          SourceTV2D.ctx.beginPath();
          SourceTV2D.ctx.arc(SourceTV2D.bombPosition[0], SourceTV2D.bombPosition[1], 50*SourceTV2D.scaling, 0, Math.PI*2, true);
          SourceTV2D.ctx.fill();
          
          SourceTV2D.ctx.fillStyle = "#FFFF00";
          SourceTV2D.ctx.beginPath();
          SourceTV2D.ctx.arc(SourceTV2D.bombPosition[0], SourceTV2D.bombPosition[1], 20*SourceTV2D.scaling, 0, Math.PI*2, true);
          SourceTV2D.ctx.fill();
          SourceTV2D.ctx.restore();
        }
        
        var d = new Date();
        var time = d.getTime();
        // Draw planted bomb on map
        if (!SourceTV2D.bombDropped && SourceTV2D.bombPlantTime > 0)
        {
          SourceTV2D.ctx.save();
          SourceTV2D.ctx.fillStyle = "#FF4500";
          SourceTV2D.ctx.beginPath();
          SourceTV2D.ctx.arc(SourceTV2D.bombPosition[0], SourceTV2D.bombPosition[1], 9*SourceTV2D.scaling, 0, Math.PI*2, true);
          SourceTV2D.ctx.fill();
          
          SourceTV2D.ctx.strokeStyle = "rgb(255,0,0)";
          SourceTV2D.ctx.beginPath();
          SourceTV2D.ctx.arc(SourceTV2D.bombPosition[0], SourceTV2D.bombPosition[1], 9*SourceTV2D.scaling, 0, Math.PI*2, true);
          SourceTV2D.ctx.stroke();
          
          SourceTV2D.ctx.font = Math.round(8*SourceTV2D.scaling) + "pt Verdana";
          SourceTV2D.ctx.fillStyle = "#FFFFFF";
          SourceTV2D.ctx.fillText("B", SourceTV2D.bombPosition[0]-4*SourceTV2D.scaling, SourceTV2D.bombPosition[1] + 3*SourceTV2D.scaling);
          
          if (!SourceTV2D.bombExploded)
          {
            SourceTV2D.ctx.font = Math.round(8*SourceTV2D.scaling) + "pt Verdana";
            SourceTV2D.ctx.fillStyle = "#FFFFFF";
            var bombTimeLeft;
            // Not yet defused? Count down!
            if (SourceTV2D.bombDefuseTime == -1)
              bombTimeLeft = Math.round(SourceTV2D.bombExplodeTime-time/1000 + SourceTV2D.bombPlantTime);
            // The bomb has been defused. Stay on the current time
            else
              bombTimeLeft = Math.round(SourceTV2D.bombDefuseTime - SourceTV2D.bombPlantTime);
            if (bombTimeLeft < 0)
              bombTimeLeft = 0;
            SourceTV2D.ctx.fillText("" + bombTimeLeft, SourceTV2D.bombPosition[0]-4*SourceTV2D.scaling, SourceTV2D.bombPosition[1]-15*SourceTV2D.scaling);          
          }
          SourceTV2D.ctx.restore();
        }
        
        // Set this for the player names
        SourceTV2D.ctx.font = Math.round(10*SourceTV2D.scaling) + "pt Verdana";
        for(var i=0;i<SourceTV2D.players.length;i++)
        {
            // Make sure we're in sync with the other messages..
            // Delete older frames
            while(SourceTV2D.players[i].positions.length > 0 && (time - SourceTV2D.players[i].positions[0].time) > 2000)
            {
              SourceTV2D.players[i].positions.splice(0,1);
            }
			
            // There is no coordinate for this player yet
            if (SourceTV2D.players[i].positions.length == 0)
                //debug("No co-ords for player idx " + i);
                continue;
            
            SourceTV2D.ctx.save();
			
            if (SourceTV2D.players[i].team < 2)
                SourceTV2D.ctx.fillStyle = "black";
            else if (SourceTV2D.players[i].team == 2)
            {
                if (SourceTV2D.players[i].positions[0].diedhere == false)
                    SourceTV2D.ctx.fillStyle = "red";
                else
                    SourceTV2D.ctx.fillStyle = "rgba(255,0,0,0.3)";
            }
            else if (SourceTV2D.players[i].team == 3)
            {
                if (SourceTV2D.players[i].positions[0].diedhere == false)
                    SourceTV2D.ctx.fillStyle = "blue";
                else
                    SourceTV2D.ctx.fillStyle = "rgba(0,0,255,0.3)";
            }
            
            // Teleport directly to new spawn, if he died at this position
            if (SourceTV2D.players[i].positions[0].diedhere)
            {
                if (SourceTV2D.players[i].positions[1])
                {
                    //if (time >= SourceTV2D.players[i].positions[1].time)
                        SourceTV2D.players[i].positions.splice(0,1);
                }
            }
            // Move the player smoothly towards the new position
            else if (SourceTV2D.players[i].positions.length > 1)
            {
                if (SourceTV2D.players[i].positions[0].x == SourceTV2D.players[i].positions[1].x
                && SourceTV2D.players[i].positions[0].y == SourceTV2D.players[i].positions[1].y)
                {
                    //if (time >= SourceTV2D.players[i].positions[1].time)
                        SourceTV2D.players[i].positions.splice(0,1);
                }
                else
                {
                    // This function is called 20x a second
                    if (SourceTV2D.players[i].positions[0].swapx == null)
                    {
                        SourceTV2D.players[i].positions[0].swapx = SourceTV2D.players[i].positions[0].x > SourceTV2D.players[i].positions[1].x?-1:1;
                        SourceTV2D.players[i].positions[0].swapy = SourceTV2D.players[i].positions[0].y > SourceTV2D.players[i].positions[1].y?-1:1;
                    }
                    if (SourceTV2D.players[i].positions[0].diffx == null)
                    {
                        var timediff = SourceTV2D.players[i].positions[1].time - SourceTV2D.players[i].positions[0].time;
                        SourceTV2D.players[i].positions[0].diffx = Math.abs(SourceTV2D.players[i].positions[1].x - SourceTV2D.players[i].positions[0].x)/(timediff/50);
                        SourceTV2D.players[i].positions[0].diffy = Math.abs(SourceTV2D.players[i].positions[1].y - SourceTV2D.players[i].positions[0].y)/(timediff/50);
                    }
                    
                    var x = SourceTV2D.players[i].positions[0].x + SourceTV2D.players[i].positions[0].swapx*SourceTV2D.players[i].positions[0].diffx;
                    var y = SourceTV2D.players[i].positions[0].y + SourceTV2D.players[i].positions[0].swapy*SourceTV2D.players[i].positions[0].diffy;
                    
                    // We're moving too far...
                    if ((SourceTV2D.players[i].positions[0].swapx==-1 && x <= SourceTV2D.players[i].positions[1].x)
                    || (SourceTV2D.players[i].positions[0].swapx==1 && x >= SourceTV2D.players[i].positions[1].x)
                    || (SourceTV2D.players[i].positions[0].swapy==-1 && y <= SourceTV2D.players[i].positions[1].y)
                    || (SourceTV2D.players[i].positions[0].swapy==1 && y >= SourceTV2D.players[i].positions[1].y))
                    {
                        SourceTV2D.players[i].positions.splice(0,1);
                    }
                    else
                    {
                        SourceTV2D.players[i].positions[0].x = x;
                        SourceTV2D.players[i].positions[0].y = y;
                    }
                }
            }
            
            var playerRadius = SourceTV2D.playerRadius;
            // User hovers his mouse over this player
            if (SourceTV2D.players[i].hovered || SourceTV2D.players[i].selected)
            {
                playerRadius = SourceTV2D.playerRadius + 4*SourceTV2D.scaling;
                SourceTV2D.ctx.save();
                SourceTV2D.ctx.beginPath();
                SourceTV2D.ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
                SourceTV2D.ctx.arc(SourceTV2D.players[i].positions[0].x, SourceTV2D.players[i].positions[0].y, playerRadius + 2*SourceTV2D.scaling, 0, Math.PI*2, true);
                SourceTV2D.ctx.fill();
                SourceTV2D.ctx.restore();
            }

            // Draw player itself
            SourceTV2D.ctx.beginPath();
            SourceTV2D.ctx.arc(SourceTV2D.players[i].positions[0].x, SourceTV2D.players[i].positions[0].y, playerRadius, 0, Math.PI*2, true);
            SourceTV2D.ctx.fill();
            
            // He got hurt this frame
            if (SourceTV2D.players[i].positions[0].hurt)
            {
                SourceTV2D.ctx.strokeStyle = "rgb(230, 149, 0)";
                SourceTV2D.ctx.beginPath();
                SourceTV2D.ctx.arc(SourceTV2D.players[i].positions[0].x, SourceTV2D.players[i].positions[0].y, playerRadius, 0, Math.PI*2, true);
                SourceTV2D.ctx.stroke();
            }
            
            // Display player names above their heads
            var bShowHealthBar = (SourceTV2D.players[i].health > 0 && $("#healthbars").attr('checked'));
            //if ($("#names").attr('checked'))
            if (1)
            {
                SourceTV2D.ctx.save();
                var nameWidth = SourceTV2D.ctx.measureText(SourceTV2D.players[i].name).width;
                SourceTV2D.ctx.translate(SourceTV2D.players[i].positions[0].x-(nameWidth/2), SourceTV2D.players[i].positions[0].y-(bShowHealthBar?16:10)*SourceTV2D.scaling);
                SourceTV2D.ctx.fillText(SourceTV2D.players[i].name, 0, 0);
                SourceTV2D.ctx.restore();
            }
            
            // Draw view angle as white dot
            SourceTV2D.ctx.translate(SourceTV2D.players[i].positions[0].x, SourceTV2D.players[i].positions[0].y);
            SourceTV2D.ctx.fillStyle = "white";
            SourceTV2D.ctx.rotate(SourceTV2D.players[i].positions[0].angle);
            SourceTV2D.ctx.beginPath();
            SourceTV2D.ctx.arc(0, Math.round(3 * SourceTV2D.scaling), Math.round(2 * SourceTV2D.scaling), 0, Math.PI*2, true);
            SourceTV2D.ctx.fill();
            
            SourceTV2D.ctx.restore();
            
            // Draw health bars
            if (bShowHealthBar)
            {
                SourceTV2D.ctx.save();
                SourceTV2D.ctx.translate(SourceTV2D.players[i].positions[0].x-12*SourceTV2D.scaling, SourceTV2D.players[i].positions[0].y-12*SourceTV2D.scaling);
                SourceTV2D.ctx.beginPath();
                SourceTV2D.ctx.strokeStyle = "rgba(0, 0, 0, 0.7)";
                SourceTV2D.ctx.rect(0, 0, 24*SourceTV2D.scaling, 4*SourceTV2D.scaling);
                SourceTV2D.ctx.stroke();
                
                var width = (24*SourceTV2D.players[i].health/100)*SourceTV2D.scaling;
                if (width > 0)
                {
                    SourceTV2D.ctx.beginPath();
                    
                    if (SourceTV2D.players[i].health >= 70)
                        SourceTV2D.ctx.fillStyle = "rgba(0, 255, 0, 0.7)";
                    else if (SourceTV2D.players[i].health >= 30)
                        SourceTV2D.ctx.fillStyle = "rgba(255, 255, 50, 0.7)";
                    else
                        SourceTV2D.ctx.fillStyle = "rgba(255, 0, 0, 0.7)";
                    
                    SourceTV2D.ctx.rect(0, 0, width, 4*SourceTV2D.scaling);
                    SourceTV2D.ctx.fill();
                }
                
                SourceTV2D.ctx.restore();
            }
        }
        
        // Draw the round end info box
        if (SourceTV2D.roundEnded != -1)
        {
            SourceTV2D.ctx.save();
            SourceTV2D.ctx.font = Math.round(32*SourceTV2D.scaling) + "pt Verdana";

            var winnertext = SourceTV2D.team[SourceTV2D.roundEnded] + " won the round!";
            
            // Draw a box around it
            SourceTV2D.ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
            SourceTV2D.ctx.beginPath();
            SourceTV2D.ctx.rect(SourceTV2D.width/2-SourceTV2D.ctx.measureText(winnertext).width/2-5, SourceTV2D.height/2*SourceTV2D.scaling-34, SourceTV2D.ctx.measureText(winnertext).width + 10, 40);
            SourceTV2D.ctx.fill();
            
            SourceTV2D.ctx.fillStyle = "rgb(255,255,255)";
            SourceTV2D.ctx.fillText(winnertext, SourceTV2D.width/2-SourceTV2D.ctx.measureText(winnertext).width/2, SourceTV2D.height/2*SourceTV2D.scaling);
            
            SourceTV2D.ctx.restore();
        }
        
        // Draw the round time
        if (SourceTV2D.game == "cstrike" && SourceTV2D.mp_roundtime > 0 && SourceTV2D.roundStartTime > 0)
        {
            SourceTV2D.ctx.save();
            SourceTV2D.ctx.font = Math.round(14*SourceTV2D.scaling) + "pt Verdana";
            SourceTV2D.ctx.fillStyle = "rgb(255,255,255)";
            var timeleft = 0;
            // Stop the counting on round end
            if (SourceTV2D.roundEndTime > 0)
            {
                timeleft = SourceTV2D.mp_roundtime - SourceTV2D.roundEndTime + SourceTV2D.roundStartTime;
            }
            else
            {
                var d = new Date();
                timeleft = SourceTV2D.mp_roundtime - Math.floor(d.getTime()/1000) + SourceTV2D.roundStartTime;
            }
            if (timeleft < 0)
                timeleft = 0;
            var timetext = "Timeleft: ";
            var minutes = Math.floor(timeleft/60);
            if (minutes < 10)
                timetext += "0";
            timetext += minutes + ":";
            var seconds = (timeleft%60);
            if (seconds < 10)
                timetext += "0";
            timetext += seconds;
            SourceTV2D.ctx.fillText(timetext, SourceTV2D.width-SourceTV2D.ctx.measureText(timetext).width-50*SourceTV2D.scaling, SourceTV2D.height-50*SourceTV2D.scaling);
            
            SourceTV2D.ctx.restore();
        }
        
        // Draw the scoreboard
        if (SourceTV2D.spacebarPressed)
        {
            SourceTV2D.ctx.save();
            SourceTV2D.ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
            SourceTV2D.ctx.strokeStyle = "rgb(255,165,0)";
            SourceTV2D.ctx.translate(SourceTV2D.width*0.1, SourceTV2D.height*0.1);
            
            // Box with border
            SourceTV2D.ctx.beginPath();
            SourceTV2D.ctx.rect(0, 0, SourceTV2D.width*0.8, SourceTV2D.height*0.8);
            SourceTV2D.ctx.fill();
            SourceTV2D.ctx.beginPath();
            SourceTV2D.ctx.rect(0, 0, SourceTV2D.width*0.8, SourceTV2D.height*0.8);
            SourceTV2D.ctx.stroke();
            
            SourceTV2D.ctx.translate(10*SourceTV2D.scaling, 0);
            
            // Map and servername
            SourceTV2D.ctx.font = Math.round(12*SourceTV2D.scaling) + "pt Verdana";
            SourceTV2D.ctx.fillStyle = "rgba(255,165,0,0.9)";
            SourceTV2D.ctx.fillText(SourceTV2D.map + "  Server: " + SourceTV2D.servername, 0, 30*SourceTV2D.scaling);
            
            // Blue team header box
            SourceTV2D.ctx.beginPath();
            SourceTV2D.ctx.fillStyle = "rgba(69, 171, 255, 0.7)";
            SourceTV2D.ctx.rect(0, 50*SourceTV2D.scaling, (SourceTV2D.width*0.8)/2-10*SourceTV2D.scaling, 80*SourceTV2D.scaling);
            SourceTV2D.ctx.fill();
            SourceTV2D.ctx.beginPath();
            SourceTV2D.ctx.strokeStyle = "rgba(255, 255, 255, 0.7)";
            SourceTV2D.ctx.rect(0, 50*SourceTV2D.scaling, (SourceTV2D.width*0.8)/2-10*SourceTV2D.scaling, 80*SourceTV2D.scaling);
            SourceTV2D.ctx.stroke();
            
            SourceTV2D.ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
            SourceTV2D.ctx.font = Math.round(18*SourceTV2D.scaling) + "pt Verdana";
            // Team name
            SourceTV2D.ctx.fillText(SourceTV2D.team[3], 10*SourceTV2D.scaling, 90*SourceTV2D.scaling);
            
            // Player count in team
            SourceTV2D.ctx.font = Math.round(14*SourceTV2D.scaling) + "pt Verdana";
            SourceTV2D.ctx.fillText(SourceTV2D.teamPlayersAlive[1] + "/" + SourceTV2D.teamPlayerAmount[2] + " players alive", 16*SourceTV2D.scaling, 120*SourceTV2D.scaling);
            
            // Team points
            SourceTV2D.ctx.font = Math.round(36*SourceTV2D.scaling) + "pt Verdana";
            SourceTV2D.ctx.fillText(SourceTV2D.teamPoints[1] + "", (SourceTV2D.width*0.8)/2-16*SourceTV2D.scaling-SourceTV2D.ctx.measureText(SourceTV2D.teamPoints[1] + "").width, 120*SourceTV2D.scaling);
            
            // Table header
            SourceTV2D.ctx.fillStyle = "rgba(69, 171, 255, 0.9)";
            SourceTV2D.ctx.font = Math.round(10*SourceTV2D.scaling) + "pt Verdana";
            SourceTV2D.ctx.fillText("Player", 10*SourceTV2D.scaling, 150*SourceTV2D.scaling);
            var deathWidth = SourceTV2D.ctx.measureText("Deaths").width;
            SourceTV2D.ctx.fillText("Deaths", (SourceTV2D.width*0.8)/2-20*SourceTV2D.scaling-deathWidth, 150*SourceTV2D.scaling);
            var fragsWidth = SourceTV2D.ctx.measureText("Frags").width;
            SourceTV2D.ctx.fillText("Frags", (SourceTV2D.width*0.8)/2-28*SourceTV2D.scaling-deathWidth-fragsWidth, 150*SourceTV2D.scaling);
            
            // Player list border
            SourceTV2D.ctx.strokeStyle = "rgba(69, 171, 255, 0.9)";
            SourceTV2D.ctx.beginPath();
            var iListBorderHeight = SourceTV2D.height*0.8-200*SourceTV2D.scaling;
            SourceTV2D.ctx.rect(0, 160*SourceTV2D.scaling, (SourceTV2D.width*0.8)/2-10*SourceTV2D.scaling, iListBorderHeight);
            SourceTV2D.ctx.stroke();
            
            // Player list
            SourceTV2D.ctx.font = Math.round(14*SourceTV2D.scaling) + "pt Verdana";
            var iOffset = 0;
            for(var i=0;i<SourceTV2D.players.length;i++)
            {
                if (SourceTV2D.players[i].team != 3)
                    continue;
                
                var iHeight = (180 + 20*iOffset)*SourceTV2D.scaling;
                if (iHeight > iListBorderHeight)
                    break;
                
                if (SourceTV2D.players[i].alive)
                  SourceTV2D.ctx.fillStyle = "rgba(69, 171, 255, 0.9)";
                else
                  SourceTV2D.ctx.fillStyle = "rgba(69, 171, 255, 0.6)";
                
                SourceTV2D.ctx.fillText(SourceTV2D.players[i].name, 10*SourceTV2D.scaling, iHeight);
                SourceTV2D.ctx.fillText(SourceTV2D.players[i].deaths, (SourceTV2D.width*0.8)/2-20*SourceTV2D.scaling-deathWidth, iHeight);
                SourceTV2D.ctx.fillText(SourceTV2D.players[i].frags, (SourceTV2D.width*0.8)/2-28*SourceTV2D.scaling-deathWidth-fragsWidth, iHeight);
                if (SourceTV2D.players[i].got_defuser)
                    SourceTV2D.ctx.fillText("D", (SourceTV2D.width*0.8)/2-66*SourceTV2D.scaling-deathWidth-fragsWidth, iHeight);
                iOffset++;
            }
            
            // Red team!
            SourceTV2D.ctx.save();
            SourceTV2D.ctx.translate((SourceTV2D.width*0.8)/2, 0);
            
            // Red team header box
            SourceTV2D.ctx.beginPath();
            SourceTV2D.ctx.fillStyle = "rgba(207, 68, 102, 0.7)";
            SourceTV2D.ctx.rect(0, 50*SourceTV2D.scaling, (SourceTV2D.width*0.8)/2-20*SourceTV2D.scaling, 80*SourceTV2D.scaling);
            SourceTV2D.ctx.fill();
            SourceTV2D.ctx.beginPath();
            SourceTV2D.ctx.strokeStyle = "rgba(255, 255, 255, 0.7)";
            SourceTV2D.ctx.rect(0, 50*SourceTV2D.scaling, (SourceTV2D.width*0.8)/2-20*SourceTV2D.scaling, 80*SourceTV2D.scaling);
            SourceTV2D.ctx.stroke();
            
            SourceTV2D.ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
            SourceTV2D.ctx.font = Math.round(18*SourceTV2D.scaling) + "pt Verdana";
            // Team name
            SourceTV2D.ctx.fillText(SourceTV2D.team[2], (SourceTV2D.width*0.8)/2-31*SourceTV2D.scaling-SourceTV2D.ctx.measureText(SourceTV2D.team[2]).width, 90*SourceTV2D.scaling);
            
            // Player count in team
            SourceTV2D.ctx.font = Math.round(14*SourceTV2D.scaling) + "pt Verdana";
            var sBuf = "players alive " + SourceTV2D.teamPlayersAlive[0] + "/" + SourceTV2D.teamPlayerAmount[1];
            SourceTV2D.ctx.fillText(sBuf, (SourceTV2D.width*0.8)/2-37*SourceTV2D.scaling-SourceTV2D.ctx.measureText(sBuf).width, 120*SourceTV2D.scaling);
            
            // Team points
            SourceTV2D.ctx.font = Math.round(36*SourceTV2D.scaling) + "pt Verdana";
            SourceTV2D.ctx.fillText(SourceTV2D.teamPoints[0] + "", 5*SourceTV2D.scaling, 120*SourceTV2D.scaling);
            
            // Table header
            SourceTV2D.ctx.fillStyle = "rgba(207, 68, 102, 0.9)";
            SourceTV2D.ctx.font = Math.round(10*SourceTV2D.scaling) + "pt Verdana";
            SourceTV2D.ctx.fillText("Player", 10*SourceTV2D.scaling, 150*SourceTV2D.scaling);
            var deathWidth = SourceTV2D.ctx.measureText("Deaths").width;
            SourceTV2D.ctx.fillText("Deaths", (SourceTV2D.width*0.8)/2-30*SourceTV2D.scaling-deathWidth, 150*SourceTV2D.scaling);
            var fragsWidth = SourceTV2D.ctx.measureText("Frags").width;
            SourceTV2D.ctx.fillText("Frags", (SourceTV2D.width*0.8)/2-38*SourceTV2D.scaling-deathWidth-fragsWidth, 150*SourceTV2D.scaling);
            
            // Player list border
            SourceTV2D.ctx.strokeStyle = "rgba(207, 68, 102, 0.9)";
            SourceTV2D.ctx.beginPath();
            var iListBorderHeight = SourceTV2D.height*0.8-200*SourceTV2D.scaling;
            SourceTV2D.ctx.rect(0, 160*SourceTV2D.scaling, (SourceTV2D.width*0.8)/2-20*SourceTV2D.scaling, iListBorderHeight);
            SourceTV2D.ctx.stroke();
            
            // Player list
            SourceTV2D.ctx.font = Math.round(14*SourceTV2D.scaling) + "pt Verdana";
            iOffset = 0;
            for(var i=0;i<SourceTV2D.players.length;i++)
            {
                if (SourceTV2D.players[i].team != 2)
                    continue;
                
                var iHeight = (180 + 20*iOffset)*SourceTV2D.scaling;
                if (iHeight > iListBorderHeight)
                    break;
                
                if (SourceTV2D.players[i].alive)
                  SourceTV2D.ctx.fillStyle = "rgba(207, 68, 102, 0.9)";
                else
                  SourceTV2D.ctx.fillStyle = "rgba(207, 68, 102, 0.6)";
                
                SourceTV2D.ctx.fillText(SourceTV2D.players[i].name, 10*SourceTV2D.scaling, iHeight);
                SourceTV2D.ctx.fillText(SourceTV2D.players[i].deaths, (SourceTV2D.width*0.8)/2-20*SourceTV2D.scaling-deathWidth, iHeight);
                SourceTV2D.ctx.fillText(SourceTV2D.players[i].frags, (SourceTV2D.width*0.8)/2-28*SourceTV2D.scaling-deathWidth-fragsWidth, iHeight);
                if (SourceTV2D.players[i].got_the_bomb)
                    SourceTV2D.ctx.fillText("B", (SourceTV2D.width*0.8)/2-66*SourceTV2D.scaling-deathWidth-fragsWidth, iHeight);
                iOffset++;
            }
            
            SourceTV2D.ctx.restore();
            
            // Spectators
            iOffset = 10*SourceTV2D.scaling + SourceTV2D.ctx.measureText(SourceTV2D.teamPlayerAmount[0] + " Spectators: ").width;
            iListBorderHeight += 185*SourceTV2D.scaling;
            SourceTV2D.ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
            SourceTV2D.ctx.fillText(SourceTV2D.teamPlayerAmount[0] + " Spectators: ", 10*SourceTV2D.scaling, iListBorderHeight);
            var bMoreSpectators = false;
            for(var i=0;i<SourceTV2D.players.length;i++)
            {
                if (SourceTV2D.players[i].team > 1)
                    continue;
                
                SourceTV2D.ctx.fillText((bMoreSpectators?", ":" ") + SourceTV2D.players[i].name, iOffset, iListBorderHeight);
                iOffset += SourceTV2D.ctx.measureText((bMoreSpectators?", ":" ") + SourceTV2D.players[i].name).width;
                bMoreSpectators = true;
            }
            
            SourceTV2D.ctx.restore();
        }
    }
    catch(ex) {
        debug('Error: ' + ex);
    }
}

function loadMapImageInfo(game, map) {
    "use strict";
    // Load the background map image
    SourceTV2D.background = new Image();
    $(SourceTV2D.background).load(function () {
        SourceTV2D.canvas = document.createElement('canvas');

        // Browser does not support canvas
        if (!SourceTV2D.canvas.getContext)
        {
          $("#sourcetv2d").html("<h2>Your browser does not support the canvas element.</h2>");
          return;
        }

        SourceTV2D.scaling = 1;

        SourceTV2D.playerRadius = Math.round(5 * SourceTV2D.scaling);
        SourceTV2D.width = SourceTV2D.background.width * SourceTV2D.scaling;
        SourceTV2D.height = SourceTV2D.background.height * SourceTV2D.scaling;
        SourceTV2D.canvas.setAttribute('width',SourceTV2D.width);  
        SourceTV2D.canvas.setAttribute('height',SourceTV2D.height);

        $("#sourcetv2d").append(SourceTV2D.canvas);
        $("#sourcetv2d").mousemove(function (ev) {mousemove(ev);});
        $("#sourcetv2d").click(function (ev) {mouseclick(ev);});

        SourceTV2D.ctx = SourceTV2D.canvas.getContext('2d');
        SourceTV2D.ctx.drawImage(SourceTV2D.background,0,0,SourceTV2D.width,SourceTV2D.height);

        // Get the map config
        $.ajax({
          type: 'GET',
          url: '/maps/' + SourceTV2D.game + '/' + SourceTV2D.map + '.txt',
          dataType: 'json',
          success: function (json) {
              SourceTV2D.mapsettings.xoffset = json.xoffset;
              SourceTV2D.mapsettings.yoffset = json.yoffset;
              SourceTV2D.mapsettings.flipx = json.flipx;
              SourceTV2D.mapsettings.flipy = json.flipy;
              SourceTV2D.mapsettings.scale = json.scale;
              SourceTV2D.mapsettingsLoaded = true;
          },
          error: function (jqXHR, textStatus) {
              alert("Failed.");
              SourceTV2D.mapsettingsFailed = true;
          }
        });
    }).error(function () {
        SourceTV2D.canvas = document.createElement('canvas');

        // Browser does not support canvas
        if (!SourceTV2D.canvas.getContext)
        {
          $("#sourcetv2d").html("<h2>Your browser does not support the canvas element.</h2>");
          return;
        }

        SourceTV2D.scaling = $("#scale :selected").val()/100;

        // Default height
        SourceTV2D.width = 1024 * SourceTV2D.scaling;
        SourceTV2D.height = 768 * SourceTV2D.scaling;
        SourceTV2D.canvas.setAttribute('width',SourceTV2D.width);
        SourceTV2D.canvas.setAttribute('height',SourceTV2D.height);

        $("#sourcetv2d").append(SourceTV2D.canvas);

        SourceTV2D.ctx = SourceTV2D.canvas.getContext('2d');
        SourceTV2D.background = null;
  }).attr('src', '/maps/' + SourceTV2D.game + '/' + SourceTV2D.map + '.jpg');
}

function sortScoreBoard() {
    "use strict";
    SourceTV2D.players.sort(function (a,b) {
        if (a.frags == b.frags)
            return a.deaths - b.deaths;
        return b.frags - a.frags;
    });
}

function getPlayerAtPosition(x, y) {
    "use strict";
    for(var i=0;i<SourceTV2D.players.length;i++)
    {
        if (SourceTV2D.players[i].positions[0])
        {
            if ((SourceTV2D.players[i].positions[0].x + SourceTV2D.playerRadius*2) >= x
            && SourceTV2D.players[i].positions[0].x <= x
            && (SourceTV2D.players[i].positions[0].y + SourceTV2D.playerRadius) >= y
            && (SourceTV2D.players[i].positions[0].y - SourceTV2D.playerRadius) <= y)
            {
                return i;
            }
        }
    }
    return -1;
}

function mousemove(e) {
    "use strict";
    if (SourceTV2D.socket==null || SourceTV2D.players.length == 0)
        return;
        
    var offs = $("#sourcetv2d").offset();
    var x = e.pageX-offs.left-$("#playerlist-container").width();
    if (x < 0 || x > SourceTV2D.width)
        return;
    
    var y = e.pageY-offs.top;
    
    for(var i=0;i<SourceTV2D.players.length;i++)
    {
        SourceTV2D.players[i].hovered = false;
    }
    
    $("#player").text("");
    
    var player = getPlayerAtPosition(x, y);
    if (player != -1)
    {
        $("#player").html("Target: <b>" + SourceTV2D.players[player].name + "</b>");
        SourceTV2D.players[player].hovered = true;
        return;
    }
}

function mouseclick(e) {
    "use strict";
    if (SourceTV2D.socket==null || SourceTV2D.players.length == 0)
        return;
        
    var offs = $("#sourcetv2d").offset();
    var x = e.pageX-offs.left-$("#playerlist-container").width();
    if (x < 0 || x > SourceTV2D.width)
        return;
    
    var y = e.pageY-offs.top;
    
    for(var i=0;i<SourceTV2D.players.length;i++)
    {
        SourceTV2D.players[i].selected = false;
        $("#usrid_" + SourceTV2D.players[i].userid).removeClass("selected");
    }
    $("#selectedplayer").text("");
    
    var player = getPlayerAtPosition(x, y);
    if (player != -1)
    {
        $("#usrid_" + SourceTV2D.players[player].userid).addClass("selected");
        $("#selectedplayer").html("Selected: <b>" + SourceTV2D.players[player].name + "</b>");
        SourceTV2D.players[player].selected = true;
        return;
    }
}

function selectPlayer(userid) {
    "use strict";
    for(var i=0;i<SourceTV2D.players.length;i++)
    {
        if (SourceTV2D.players[i].team > 1 && SourceTV2D.players[i].userid == userid)
        {
            for(var x=0;x<SourceTV2D.players.length;x++)
            {
                SourceTV2D.players[x].selected = false;
                $("#usrid_" + SourceTV2D.players[x].userid).removeClass("selected");
            }
            SourceTV2D.players[i].selected = true;
            $("#usrid_" + SourceTV2D.players[i].userid).addClass("selected");
            $("#selectedplayer").html("Selected: <b>" + SourceTV2D.players[i].name + "</b>");
            break;
        }
    }
}

function highlightPlayer(userid) {
    "use strict";
    for(var i=0;i<SourceTV2D.players.length;i++)
    {
        if (SourceTV2D.players[i].team > 1 && SourceTV2D.players[i].userid == userid)
        {
            for(var x=0;x<SourceTV2D.players.length;x++)
            {
                SourceTV2D.players[x].hovered = false;
            }
            SourceTV2D.players[i].hovered = true;
            $("#player").html("Target: <b>" + SourceTV2D.players[i].name + "</b>");
            break;
        }
    }
}

function unhighlightPlayer(userid) {
    for(var i=0;i<SourceTV2D.players.length;i++)
    {
        if (SourceTV2D.players[i].team > 1 && SourceTV2D.players[i].userid == userid)
        {
            SourceTV2D.players[i].hovered = false;
            $("#player").text("");
            break;
        }
    }
}

function sendChatMessage() {
  if (SourceTV2D.socket==null)
    return;
  
  if ($("#chatinput").val() == "")
    return;

  if ($("#chatnick").val() == "")
  {
    alert("You have to enter a nickname first.");
    return;
  }
  
  SourceTV2D.socket.send($("#chatnick").val() + ": " + $("#chatinput").val());
  var d = new Date();
  var timestring = "(";
  if (d.getHours() < 10)
    timestring += "0";
  timestring += d.getHours() + ":";
  if (d.getMinutes() < 10)
    timestring += "0";
  timestring += d.getMinutes() + ":";
  if (d.getSeconds() < 10)
    timestring += "0";
  timestring += d.getSeconds() + ") ";
  
  $("#chatoutput").append(document.createTextNode(timestring + $("#chatnick").val() + ": " + $("#chatinput").val()));
  $("#chatoutput").append("<br />");
  $('#chatoutput').prop('scrollTop', $('#chatoutput').prop('scrollHeight'));
  
  $("#chatinput").val("");
  $("#chatinput").focus();
}

function players() {
    // {'userid': parseInt(frame.userid), 'ip': frame.ip, 'name': frame.name, 'team': parseInt(frame.team), 'positions': [], 'alive': true};
    for(var i=0;i<SourceTV2D.players.length;i++)
    {
        debug(i + ": #" + SourceTV2D.players[i].userid + ", Name: " + SourceTV2D.players[i].name + ", IP: " + SourceTV2D.players[i].ip + ", Team: " + SourceTV2D.players[i].team + ", Alive: " + SourceTV2D.players[i].alive + ", Positions: " + SourceTV2D.players[i].positions.length);
        if (SourceTV2D.players[i].positions.length > 0)
            debug(i + ": 1x: " + SourceTV2D.players[i].positions[0].x + ", 1y: " + SourceTV2D.players[i].positions[0].y + ", 1diffx: " + SourceTV2D.players[i].positions[0].diffx + ", 1diffy: " + SourceTV2D.players[i].positions[0].diffy + ", 1swapx: " + SourceTV2D.players[i].positions[0].swapx + ", 1swapy: " + SourceTV2D.players[i].positions[0].swapy + ", diedhere: " + SourceTV2D.players[i].positions[0].diedhere);
        if (SourceTV2D.players[i].positions.length > 1)
            debug(i + ": 2x: " + SourceTV2D.players[i].positions[1].x + ", 2y: " + SourceTV2D.players[i].positions[1].y + ", 2diffx: " + SourceTV2D.players[i].positions[1].diffx + ", 2diffy: " + SourceTV2D.players[i].positions[1].diffy + ", 2swapx: " + SourceTV2D.players[i].positions[1].swapx + ", 2swapy: " + SourceTV2D.players[i].positions[1].swapy + ", diedhere: " + SourceTV2D.players[i].positions[1].diedhere);
    }
    debug("");
}