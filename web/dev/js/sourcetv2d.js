
/*
    Livelogs SourceTV2D Browser client
    
    
    
    
    Credit to Jannik 'Peace-Maker' Hartung @ http://www.wcfan.de/ for the original code
    
    
    TF2 class index:
    CLASS NUMBER:NAME
    1: Scout
    3: Soldier
    7: Pyro
    4: Demoman
    6: Heavy
    9: Engineer
    5: Medic
    2: Sniper
    8: Spy

*/



var SourceTV2D = SourceTV2D || (function() {
    "use strict";
    return {
        init : function() {
            this.socket = null;
            this.canvas = null;
            this.background = null;
            this.ctx = null;
            this.game = null;
            this.map = null;
            this.servername = "";
            this.classnames = ["????", "Scout", "Sniper", "Soldier", "Demo", "Medic", "Heavy", "Pyro", "Spy", "Engi"]; //corresponding to the indices of classes
            this.team = ["Unassigned", "Spectator", "", ""];
            this.teamPoints = [0, 0];
            this.teamPlayerAmount = [0, 0, 0];
            this.teamPlayersAlive = [0, 0];
            this.players = [];
            this.mapsettingsLoaded = false;
            this.mapsettingsFailed = false;
            this.mapsettings = {};
            this.scaling = 0.8;
            this.playerRadius = 5;
            this.width = 0;
            this.height = 0;
            this.timer = null;
            this.roundEnded = -1;
            this.roundEndTime = -1;
            this.roundStartTime = -1;
            this.mp_roundtime = -1;
            this.frags = [];
            this.fragFadeTime = 5;
            this.infos = [];
            this.infosFadeTime = 6;
            this.chat = [];
            this.chatHoldTime = 10;
            this.chatFadeTime = 2;
            this.totalUsersWatching = 0;
            this.shownames = true;
            $("sourcetv2d").mousemove = null;


            this.intelDropped = false;
            this.intelCaptured = false;
        },

        connect : function(ip, port) {
            if (this.socket !== undefined) {
                this.disconnect();  
            }

            if (this.canvas !== null)
            {
                $(this.canvas).remove();
                this.canvas = null;
            }

            this.init();

            $("#debug").html("");

            this.ip = ip;
            this.port = port;

            var host = "ws://" + ip + ":" + port + "/sourcetv2d";
            try
            {
                if (!window.WebSocket) {
                    this.debug("Your browser doesn't support WebSockets.");
                    return;
                } else {
                    this.socket = new WebSocket(host);
                }
                
                this.debug("Opening connection to " + ip + ":" + port);
                
                this.socket.onopen = function (msg)
                {
                    this.debug("Connection established " + msg);
                };
                
                this.socket.onmessage = function (msg) { SourceTV2D.onSocketMessage(msg); };
                
                    
                this.socket.onerror = function (msg)
                {
                    if (this.ctx !== null)
                    {
                        this.ctx.font = Math.round(22*this.scaling) + "pt Verdana";
                        this.ctx.fillStyle = "rgb(255,255,255)";
                        this.ctx.fillText("Disconnected.", 100*this.scaling, 100*this.scaling);
                    }
                    this.debug("Socket reported error! " + msg);
                };
                this.socket.onclose = function (msg)
                {
                    if (this.ctx !== null)
                    {
                        this.ctx.font = Math.round(22*this.scaling) + "pt Verdana";
                        this.ctx.fillStyle = "rgb(255,255,255)";
                        this.ctx.fillText("Disconnected.", 100*this.scaling, 100*this.scaling);
                    }
                    this.debug("Disconnected - readyState: " + this.readyState + " Code: " + msg.code + ". Reason:" + msg.reason + " - wasClean: " + msg.wasClean);
                };
            }
            catch(ex) {
                this.debug('Error: ' + ex);
            }
        },

        onSocketMessage : function(msg) {
            var frame = {}, msg_data, split = null, idx, d, time;

            var i = 0; //used in all for loops

            frame.type = msg.data.charAt(0);
            msg_data = msg.data.slice(1); //will get data from position 1 to strlen(msg.data), i.e all the needed information (strips the frame type)

            if (frame.type !== "O") {
                this.debug("Received frame type: " + frame.type + " Msg: " + msg.data);
            }

            switch (frame.type)
            {
                // Initialisation
                case "I":
                    //IGAME:MAP:TEAM2NAME:TEAM3NAME:HOSTNAME
                    //we have all data in msg_data, so it can easily be tokenized

                    split = msg_data.split(':');
                    
                    frame.game = split[0];
                    frame.map = split[1];
                    frame.team1 = split[2];
                    frame.team2 = split[3];
                    frame.team1score = split[4];
                    frame.team2score = split[5];
                    frame.hostname = split[6];

                    this.debug("Game: " + frame.game);
                    this.debug("Map: " + frame.map);
                    this.debug("Team 2: " + frame.team1 + " Score: " + frame.team1score);
                    this.debug("Team 3: " + frame.team2 + " Score: " + frame.team2score);
                    
                    this.game = frame.game;
                    this.map = frame.map;
                    this.servername = frame.hostname;

                    this.team[2] = frame.team1;
                    this.team[3] = frame.team2;
                    
                    this.teamPoints[0] = frame.team1score;
                    this.teamPoints[1] = frame.team2score;

                    this.loadMapImageInfo(frame.game, frame.map);
                    
                    this.timer = setInterval(this.drawMap(this), 50);
                    
                    this.totalUsersWatching += 1;

                    break;
                
                // Map changed
                case "M":
                    //Mmap
                    frame.map = msg_data;
                    
                    if (this.canvas !== null)
                    {
                        $(this.canvas).remove();
                        this.canvas = null;
                    }

                    this.map = frame.map;
                    this.background = null;
                    this.mapsettingsLoaded = false;
                    this.mapsettingsFailed = false;
                    this.teamPoints[0] = this.teamPoints[1] = 0;
                    this.roundEnded = -1;
                    
                    this.loadMapImageInfo();
                    
                    break;
                
                // Player connected.
                case "C":
                    //CUSERID:IP:TEAM:ALIVE:FRAGS:DEATHS:HEALTH:CLASS:INTEL:NAME
                    split = msg_data.split(':');

                    frame.userid = split[0];
                    frame.ip = split[1];
                    frame.team = split[2];
                    frame.alive = split[3];
                    frame.frags = split[4];
                    frame.deaths = split[5];
                    frame.health = split[6];
                    frame.pclass = split[7];
                    frame.has_intel = split[8];
                    frame.name = split[9];
                    
                    frame.team = parseInt(frame.team, 10);
                    frame.pclass = parseInt(frame.pclass, 10);
                    frame.has_intel = parseInt(frame.has_intel, 10);
                    
                    if (frame.team < 2) {
                        this.teamPlayerAmount[0] += 1;
                    } else {
                        this.teamPlayerAmount[frame.team-1] += 1;
                        this.teamPlayersAlive[frame.team-2] += 1;
                    }
                    
                    frame.alive = parseInt(frame.alive, 10);
                    frame.health = parseInt(frame.health, 10);
                    if (frame.health > 100)
                    {
                        frame.health = 100;
                    }
                    
                    // On real client connect, k/d is "x". If we just connected to the server and we retrieve the player list, it's set to the correct k/d.

                    var frags = 0;
                    if (frame.frags !== "x") {
                        frags = parseInt(frame.frags, 10);
                    }

                    var deaths = 0;
                    if (frame.deaths !== "x") {
                        deaths = parseInt(frame.deaths, 10);
                    }
                    
                    idx = this.players.length;
                    d = new Date();

                    this.players[idx] = {'userid': parseInt(frame.userid, 10), 'ip': frame.ip, 'name': frame.name, 'team': frame.team, 'positions': [], 'alive': (frame.alive===1), 'health': frame.health, 'hovered': false, 'selected': false, 'frags': frags, 'deaths': deaths, 'pclass': frame.pclass, 'has_intel': (frame.has_intel===1)};
                    // Only show the connect message, if he's newly joined -> no team yet.
                    if (this.players[idx].team === 0) {
                        this.infos[this.infos.length] = {'msg': frame.name + " has joined the server", 'time': d.getTime()/1000};
                    }
                    
                    //var playerList = $("#players" + (this.players[idx].team===0?1:this.players[idx].team));
                    //playerList.html(playerList.html() + "<div class=\"player\" id=\"usrid_" + this.players[idx].userid + "\" onclick=\"selectPlayer(" + this.players[idx].userid + ");\" onmouseover=\"highlightPlayer(" + this.players[idx].userid + ");\" onmouseout=\"unhighlightPlayer(" + this.players[idx].userid + ");\">" + this.players[idx].name + "</div>");
                    
                    this.sortScoreboard();

                    break;
                
                // Player disconnected
                case "D":
                    //Duserid
                    frame.userid = msg_data;
                    
                    frame.userid = parseInt(frame.userid, 10);
                    //debug("Player disconnected: #" + frame.userid);
                    
                    d = new Date();
                    for (i = 0; i<this.players.length; i++) {
                        if (this.players[i].userid === frame.userid)
                        {
                            if (this.players[i].team < 2) {
                                this.teamPlayerAmount[0] -= 1;
                            } else {
                                this.teamPlayerAmount[this.players[i].team-1] -= 1;
                                if (this.players[i].alive) {
                                    this.teamPlayersAlive[this.players[i].team-2] -= 1;
                                }
                            }
                            this.infos[this.infos.length] = {'msg': this.players[i].name + " has left the server", 'time': d.getTime()/1000};

                            // Handle our player list
                            //$("#usrid_" + frame.userid).remove();
                            //if (this.players[i].selected)
                            //    $("#selectedplayer").html("");

                            this.players.splice(i, 1);

                            break;
                        }
                    }
                    this.sortScoreboard();
                    //if (window.console && window.console.log)
                    //    window.console.log("Player disconnected: #" + frame.userid);
                    break;
                
                // Player changed team
                case "T":
                    //Tuserid:team
                    split = msg_data.split(':');

                    frame.userid = split[0];
                    frame.team = split[1];

                    frame.userid = parseInt(frame.userid, 10);
                    frame.team = parseInt(frame.team, 10);
                    
                    //get player's index
                    idx = -1;
                    for (i = 0; i<this.players.length; i++) {
                        if (this.players[i].userid === frame.userid)
                        {
                            idx = i;
                            break;
                        }
                    }

                    if (idx !== -1)
                    {
                        //Player is valid, and he joined team "team"
                        if (frame.team < 2) {
                            this.teamPlayerAmount[0] += 1; //spec/unassigned
                        } else {
                            this.teamPlayerAmount[frame.team-1] += 1;
                            if (this.players[idx].alive) {
                                this.teamPlayersAlive[frame.team-2] += 1;
                            }
                        }

                        //Left the other team
                        if (this.players[idx].team < 2) {
                            this.teamPlayerAmount[0] -= 1;
                        } else {
                            this.teamPlayerAmount[this.players[idx].team-1] -= 1;
                            if (this.players[idx].alive) {
                                this.teamPlayersAlive[this.players[idx].team-2] -= 1;
                            }
                        }
                        
                        // Handle our player list
                        //$("#players" + (frame.team===0?1:frame.team)).append($("#usrid_" + frame.userid));
                        
                        d = new Date();
                        this.players[idx].team = frame.team;
                        this.infos[this.infos.length] = {'msg': this.players[idx].name + " changed team to " + this.team[this.players[idx].team], 'time': d.getTime()/1000};
                        
                        if (this.players[idx].team < 2) {
                            this.players[idx].positions.clear();
                        }
                        
                        //debug("Player #" + frame.userid + " changed team to: " + this.players[idx].team);
                        this.sortScoreboard();
                    } else {
                        this.debug("NOT FOUND!!! Player #" + frame.userid + " changed team to: " + frame.team);
                    }

                    break;
                
                // Players origin updated
                case "O":
                    //Ouserid:x:y:angle|userid:x:y:angle|userid:x:y:angle|repeat
                    if (!this.mapsettingsLoaded || this.background === null) {
                        break;
                    }

                    split = msg_data.split('|');

                    frame.positions = [];

                    $.each(split, function(player_index, player_data) {
                        if (frame.positions[player_index] === undefined) {
                            frame.positions[player_index] = ['', '', '', ''];
                        }

                        var player_values = player_data.split(':');

                        $.each(player_values, function(index, value) {
                            frame.positions[player_index][index] = parseInt(value, 10);
                        });
                    });
                    
                    // Save the player positions
                    idx = -1;
                    d = new Date();
                    time = d.getTime();

                    for (i = 0; i<frame.positions.length; i++) {
                        frame.positions[i][3] += 90; //add 90 to our direction angle
                        
                        if (frame.positions[i][3] < 0) { //if angle is negative, flip to positive
                            frame.positions[i][3] *= -1;
                        }
                        else if (frame.positions[i][3] > 0) {
                            frame.positions[i][3] = 360-frame.positions[i][3];
                        }
                        
                        frame.positions[i][3] = (Math.PI/180)*frame.positions[i][3]; //convert angle to radians
                        
                        if (this.mapsettings.flipx) {
                            frame.positions[i][1] *= -1;
                        }
                        if (this.mapsettings.flipy) {
                            frame.positions[i][2] *= -1;
                        }
                        
                        frame.positions[i][1] = Math.round(((frame.positions[i][1] + this.mapsettings.xoffset) / this.mapsettings.scale) * this.scaling);
                        frame.positions[i][2] = Math.round(((frame.positions[i][2] + this.mapsettings.yoffset) / this.mapsettings.scale) * this.scaling);
                        
                        //debug("CANVAS X: " + frame.positions[i][1] + ", CANVAS Y: " + frame.positions[i][2]);
                        
                        // Get the correct team color
                        idx = -1;
                        for (var p=0; p<this.players.length; p++) {
                            if (this.players[p].userid === frame.positions[i][0])
                            {
                                idx = p;
                                break;
                            }
                        }
                        
                        if (idx !== -1)
                        {
                            this.players[idx].positions[this.players[idx].positions.length] = {'x': frame.positions[i][1], 'y': frame.positions[i][2], 'angle': frame.positions[i][3], 'time': time, 'diffx': null, 'diffy': null, 'swapx': null, 'swapy': null, 'diedhere': false, 'hurt': false};
                        }
                        
                        //debug("Player moved: #" + frame.positions[i][0] + " - x: " + frame.positions[i][1] + ", y: " + frame.positions[i][2] + ", angle: " + frame.positions[i][3]);
                    }
                    
                    break;
                
                // Round start
                case "R":
                    //Rroundtime:full_restart
                    split = msg_data.split(":");
                    
                    frame.roundstart = Number(split[0]);
                    var full_reset = split[1];
                    
                    this.roundEnded = -1;
                    this.roundEndTime = -1;
                    this.roundStartTime = frame.roundstart;
                    
                    //full reset (mp_restartgame or something?), need to clear player stats
                    if (full_reset === "1") {
                        for (i = 0; i < this.players.length; i++) {
                            this.players[i].frags = 0;
                            this.players[i].deaths = 0;
                        }
                    }
                    
                    break;
                
                // Round end
                case "E":
                    frame.winnerteam = msg_data;
                    
                    frame.winnerteam = parseInt(frame.winnerteam, 10);
                    
                    this.teamPoints[frame.winnerteam-2] += 1;
                    this.roundEnded = frame.winnerteam;
                    
                    d = new Date();
                    this.roundEndTime = Math.floor(d.getTime()/1000);
                    
                    break;
                
                // ConVar changed
                case "V":
                    
                    break;

                // Someone killed somebody
                case "K":                
                    if (this.ctx === null) {
                        break;
                    }
                    //Kvictimid:attackerid:weapon

                    split = msg_data.split(':');

                    frame.victim = split[0];
                    frame.attacker = split[1];
                    frame.weapon = split[2];
                    
                    frame.attacker = parseInt(frame.attacker, 10);
                    frame.victim = parseInt(frame.victim, 10);
                    
                    var idxV = -1;
                    var idxA = -1;
                    for (i = 0; i<this.players.length; i++) {
                        if (this.players[i].userid === frame.attacker)
                        {
                            idxA = i;
                        }
                        if (this.players[i].userid === frame.victim)
                        {
                            idxV = i;
                        }
                    }
                    
                    var attackername = "";
                    var attackerteam = 0;

                    if (frame.attacker === 0) {
                        attackername = "WORLD";
                    } else if (idxA === -1) {
                        attackername = "NotFound(#" + frame.attacker + ")";
                    } else {
                        this.players[idxA].frags += 1;
                        attackername = this.players[idxA].name;
                        attackerteam = this.players[idxA].team;
                    }
                    
                    var victimname = "";
                    var victimteam = 0;
                    if (idxV === -1) {
                        victimname = "NotFound(#" + frame.victim + ")";
                    } else {
                        victimname = this.players[idxV].name;
                        victimteam = this.players[idxV].team;
                        this.players[idxV].alive = false;
                        this.players[idxV].got_defuser = false;
                        this.players[idxV].deaths += 1;
                        this.teamPlayersAlive[this.players[idxV].team-2] -= 1;
                        if (this.players[idxV].positions.length !== 0)
                        {
                            this.players[idxV].positions[this.players[idxV].positions.length-1].diedhere = true;
                        }
                    }
                    
                    // Suicides = frags-1
                    if (idxV !== -1 && idxA !== -1 && idxV === idxA)
                    {
                        // We added one frag already above..
                        this.players[idxV].frags-=2;
                    }
                    
                    d = new Date();
                    this.frags[this.frags.length] = {'attacker': attackername, 'ateam': attackerteam, 'victim': victimname, 'vteam': victimteam, 'weapon': frame.weapon, 'time': (d.getTime()/1000)};
                    
                    this.sortScoreboard();
                    
                    //debug("Player " + attackername + " killed " + victimname + " with " + frame.weapon);
                    break;

                // Player spawned
                case "S":
                    //Sid:class
                    frame.userclass = "";
                    frame.userid = "";
                    
                    split = msg_data.split(":");
                    
                    frame.userid = split[0];
                    frame.userclass = split[1];
                    
                    idx = -1;
                    for (i = 0; i<this.players.length; i++) {
                        if (this.players[i].userid === frame.userid)
                        {
                            idx = i;
                            break;
                        }
                    }
                    if (idx !== -1)
                    {
                        if (!this.players[idx].alive) {
                            this.teamPlayersAlive[this.players[idx].team-2] += 1;
                        }
                        
                        this.players[idx].alive = true;
                        this.players[idx].health = 100;
                        this.players[idx].plant_start_time = -1;
                        this.players[idx].defuse_start_time = -1;
                        this.players[idx].pclass = frame.userclass;
                    }
                    break;
                
                // Player said something
                case "X":
                    //Xuserid:msg

                    split = msg_data.split(':');

                    frame.userid = split[0];
                    frame.msg = split[1];

                    frame.userid = parseInt(frame.userid, 10);
                    
                    // Console?
                    if (frame.userid === 0) {
                        d = new Date();
                        this.chat[this.chat.length] = {'name': "Console", 'team': 0, 'msg': frame.msg, 'time': d.getTime()/1000};
                        break;
                    }
                    
                    idx = -1;
                    for (i = 0; i<this.players.length; i++) {
                        if (this.players[i].userid === frame.userid) {
                            idx = i;
                            break;
                        }
                    }
                    if (idx !== -1)
                    {
                        d = new Date();
                        this.chat[this.chat.length] = {'name': this.players[idx].name, 'team': this.players[idx].team, 'msg': frame.msg, 'time': d.getTime()/1000};
                    }
                    //debug("Player #" + frame.userid + " said: " + frame.msg);
                    break;
                
                // Player was hurt
                case "H":
                    //Huserid:damage

                    split = msg_data.split(':');

                    frame.userid = split[0];
                    frame.dmg = split[1];

                    frame.userid = parseInt(frame.userid, 10);
                    frame.dmg = parseInt(frame.dmg, 10);
                    
                    idx = -1;
                    for (i = 0; i<this.players.length; i++)
                    {
                        if (this.players[i].userid === frame.userid)
                        {
                            idx = i;
                            break;
                        }
                    }
                    if (idx !== -1)
                    {
                        this.players[idx].health = this.players[idx].health - frame.dmg;
                        if (this.players[idx].health < 0) {
                            this.players[idx].health = 0;
                        }
                        if (this.players[idx].positions.length > 0) {
                            this.players[idx].positions[this.players[idx].positions.length-1].hurt = true;
                        }
                    }
                    break;
                
                // SourceTV2D Chat message
                case "Z":
                    //Zuser:message
                    split = msg_data.split(':');

                    frame.message = split[1];
                    frame.user = split[0];
                    
                    d = new Date();
                    var timestring = "(";
                    if (d.getHours() < 10) {
                        timestring += "0";
                    }
                    timestring += d.getHours() + ":";
                    if (d.getMinutes() < 10) {
                        timestring += "0";
                    }
                    timestring += d.getMinutes() + ":";
                    if (d.getSeconds() < 10) {
                        timestring += "0";
                    }
                    timestring += d.getSeconds() + ") ";
                    
                    $("#chatoutput").append(document.createTextNode(timestring + frame.message));
                    $("#chatoutput").append("<br />");
                    $('#chatoutput').prop('scrollTop', $('#chatoutput').prop('scrollHeight'));
                    
                    break;
                
                // SourceTV2D spectator amount changed
                case "A":
                    //Anumwatch
                    frame.totalwatching = parseInt(msg_data, 10);
                    this.totalUsersWatching = frame.totalwatching;
                    $("#totalwatching").text(this.totalUsersWatching);
                    
                    break;
                
                // Player changed his name
                case "N":
                    //Nuserid:newname

                    split = msg_data.split(':');
                    
                    frame.userid = split[0];
                    frame.name = split[1];

                    frame.userid = parseInt(frame.userid, 10);
                    
                    idx = -1;
                    for (i = 0;i<this.players.length;i++)
                    {
                        if (this.players[i].userid === frame.userid)
                        {
                            idx = i;
                            break;
                        }
                    }
                    if (idx !== -1)
                    {
                        d = new Date();
                        this.infos[this.infos.length] = {'msg': this.players[idx].name + " changed team to " + frame.name, 'time': d.getTime()/1000};
                        this.players[idx].name = frame.name;
                        $("#usrid_" + frame.userid).text(frame.name);
                    }
                    break;

                default:
                    this.debug("Unknown frame type received: " + frame.type);
            }
        },

        disconnect : function() {
            if (this.timer !== null) {
                clearInterval(this.timer);
                this.timer = null;
            }

            if (this.ctx !== null) {
                this.ctx.font = Math.round(22*this.scaling) + "pt Verdana";
                this.ctx.fillStyle = "rgb(255,255,255)";
                this.ctx.fillText("Disconnected.", 100*this.scaling, 100*this.scaling);
            }

            if (this.socket===null) {
                return;
            }
            
            this.totalUsersWatching -= 1;
            this.debug("Disconnecting from socket");

            this.socket.close(1000);
            this.socket=null;
        },

        //drawmap is called by an interval, and hence its parent is not 'this' (the sourcetv2d object), therefore we pass it
        drawMap : function(this) {
            var d, time, i, alpha, offs, iOffset, deathWidth, fragsWidth, classWidth, iListBorderHeight, iHeight, classname;
            try
            {
                if (this.ctx === null) {
                    this.debug("No canvas element present");

                    return;
                }
                // Clear the canvas.
                this.ctx.clearRect(0,0,this.width,this.height);
                if (this.background !== null) {
                    this.ctx.drawImage(this.background,0,0,this.width,this.height);
                }
                else
                {
                    this.ctx.save();
                    this.ctx.beginPath();
                    this.ctx.fillStyle = "rgb(0, 0, 0)";
                    this.ctx.rect(0, 0, this.width, this.height);
                    this.ctx.fill();
                    this.ctx.restore();
                }
                
                // Draw the kill messages
                d = new Date();
                time = d.getTime()/1000;

                this.ctx.textAlign = "left";
                this.ctx.font = Math.round(10*this.scaling) + "pt Verdana";

                for (i=0; i<this.frags.length; i++)
                {
                    if ((time - this.frags[i].time) > this.fragFadeTime)
                    {
                        this.frags.splice(i, 1);
                        i -= 1;
                        continue;
                    }
                    
                    this.ctx.save();
                    
                    alpha = 1.0 - (time - this.frags[i].time) / this.fragFadeTime;
                    
                    if (this.frags[i].ateam === 2) {
                        this.ctx.fillStyle = "rgba(255,0,0," + alpha + ")";
                    }
                    else if (this.frags[i].ateam === 3) {
                        this.ctx.fillStyle = "rgba(0,0,255," + alpha + ")";
                    }
                    
                    this.ctx.fillText(this.frags[i].attacker, (50*this.scaling), ((50 + (this.frags.length-i-1)*20)*this.scaling));
                    
                    offs = this.ctx.measureText(this.frags[i].attacker).width + 10*this.scaling;
                    this.ctx.fillStyle = "rgba(255,255,255," + alpha + ")";
                    
                    this.ctx.fillText(this.frags[i].weapon, (50*this.scaling + offs), ((50 + (this.frags.length-i-1)*20)*this.scaling));
                    
                    offs += this.ctx.measureText(this.frags[i].weapon).width + 10*this.scaling;
                    
                    if (this.frags[i].vteam === 2) {
                        this.ctx.fillStyle = "rgba(255,0,0," + alpha + ")";
                    }
                    else if (this.frags[i].vteam === 3) {
                        this.ctx.fillStyle = "rgba(0,0,255," + alpha + ")";
                    }
                    
                    this.ctx.fillText(this.frags[i].victim, (50*this.scaling + offs), ((50 + (this.frags.length-i-1)*20)*this.scaling));
                    this.ctx.restore();
                }
                
                
                // Draw the connect/disconnect messages
                this.ctx.font = Math.round(11*this.scaling) + "pt Verdana";
                for (i=0; i<this.infos.length; i++)
                {
                    if ((time - this.infos[i].time) > this.infosFadeTime)
                    {
                        this.infos.splice(i, 1);
                        i -= 1;
                        continue;
                    }
                    
                    this.ctx.save();
                    alpha = 1.0 - (time - this.infos[i].time) / this.infosFadeTime;
                    this.ctx.fillStyle = "rgba(255,255,255," + alpha + ")";
                    
                    this.ctx.fillText(this.infos[i].msg, ((this.width-this.ctx.measureText(this.infos[i].msg).width)-50*this.scaling), ((50 + (this.infos.length-i-1)*20)*this.scaling));
                    this.ctx.restore();
                }
                
                
                // Draw the chat
                d = new Date();
                time = d.getTime()/1000;
                this.ctx.textAlign = "left";
                this.ctx.font = Math.round(12*this.scaling) + "pt Verdana";
                for (i=(this.chat.length-1); i>=0; i--)
                {
                    if ((time - this.chat[i].time) > (this.chatHoldTime + this.chatFadeTime))
                    {
                        this.chat.splice(i, 1);
                        if (this.chat.length > 0) {
                            i += 1;
                        }
                        continue;
                    }
                    
                    this.ctx.save();
                    
                    alpha = 1.0;
                    if ((time - this.chat[i].time) > this.chatHoldTime) {
                        alpha = 1.0 - (time - this.chat[i].time - this.chatHoldTime) / this.chatFadeTime;
                    }
                    
                    if (this.chat[i].team === 0) {
                        this.ctx.fillStyle = "rgba(255,165,0," + alpha + ")";
                    } else if (this.chat[i].team === 1) {
                        this.ctx.fillStyle = "rgba(255,255,255," + alpha + ")";
                    } else if (this.chat[i].team === 2) {
                        this.ctx.fillStyle = "rgba(255,0,0," + alpha + ")";
                    } else if (this.chat[i].team === 3) {
                        this.ctx.fillStyle = "rgba(0,0,255," + alpha + ")";
                    }
                    
                    this.ctx.fillText(this.chat[i].name, (50*this.scaling), (this.height-(50 + (this.chat.length-i-1)*20)*this.scaling));
                    
                    offs = this.ctx.measureText(this.chat[i].name).width;
                    this.ctx.fillStyle = "rgba(255,165,0," + alpha + ")";
                    
                    this.ctx.fillText(": " + this.chat[i].msg, (50*this.scaling + offs), (this.height-(50 + (this.chat.length-i-1)*20)*this.scaling));
                    this.ctx.restore();
                }
                
                //if the mapconfig wasn't found, disconnect with msg
                if (this.background === null || this.mapsettingsFailed)
                {
                    this.ctx.save();
                    this.ctx.fillStyle = "rgb(255,255,255)";
                    this.ctx.font = Math.round(20*this.scaling) + "pt Verdana";
                    var text = "No map image";
                    this.debug(text);
                    if (this.mapsettingsFailed) {
                        text = "Map config failed to load. Player positions can not be shown.";
                        //debug(text);
                        this.ctx.fillStyle = "rgb(255,0,0)";
                    }
                    this.ctx.fillText(text, (this.width - this.ctx.measureText(text).width)/2, (this.height/2));
                    this.ctx.restore();

                    this.disconnect();

                    return;
                }
                
                // Draw intel on map
                if (this.intelDropped)
                {
                  this.ctx.save();
                  this.ctx.fillStyle = "#FF4500";
                  this.ctx.beginPath();
                  this.ctx.arc(this.bombPosition[0], this.bombPosition[1], 6*this.scaling, 0, Math.PI*2, true);
                  this.ctx.fill();
                  
                  this.ctx.strokeStyle = "#FFFFFF";
                  this.ctx.beginPath();
                  this.ctx.arc(this.bombPosition[0], this.bombPosition[1], 6*this.scaling, 0, Math.PI*2, true);
                  this.ctx.stroke();
                  
                  this.ctx.font = Math.round(7*this.scaling) + "pt Verdana";
                  this.ctx.fillStyle = "#FFFFFF";
                  this.ctx.fillText("B", this.bombPosition[0]-4*this.scaling, this.bombPosition[1] + 3);
                  this.ctx.restore();
                }
                
                if (this.intelCaptured)
                {
                  this.ctx.save();
                  this.ctx.fillStyle = "#FF8C00";
                  this.ctx.beginPath();
                  this.ctx.arc(this.bombPosition[0], this.bombPosition[1], 50*this.scaling, 0, Math.PI*2, true);
                  this.ctx.fill();
                  
                  this.ctx.fillStyle = "#FFFF00";
                  this.ctx.beginPath();
                  this.ctx.arc(this.bombPosition[0], this.bombPosition[1], 20*this.scaling, 0, Math.PI*2, true);
                  this.ctx.fill();
                  this.ctx.restore();
                }
                
                d = new Date();
                time = d.getTime();
                // Draw planted bomb on map
                if (!this.bombDropped && this.bombPlantTime > 0)
                {
                  this.ctx.save();
                  this.ctx.fillStyle = "#FF4500";
                  this.ctx.beginPath();
                  this.ctx.arc(this.bombPosition[0], this.bombPosition[1], 9*this.scaling, 0, Math.PI*2, true);
                  this.ctx.fill();
                  
                  this.ctx.strokeStyle = "rgb(255,0,0)";
                  this.ctx.beginPath();
                  this.ctx.arc(this.bombPosition[0], this.bombPosition[1], 9*this.scaling, 0, Math.PI*2, true);
                  this.ctx.stroke();
                  
                  this.ctx.font = Math.round(8*this.scaling) + "pt Verdana";
                  this.ctx.fillStyle = "#FFFFFF";
                  this.ctx.fillText("B", this.bombPosition[0]-4*this.scaling, this.bombPosition[1] + 3*this.scaling);
                  
                  if (!this.bombExploded)
                  {
                    this.ctx.font = Math.round(8*this.scaling) + "pt Verdana";
                    this.ctx.fillStyle = "#FFFFFF";
                    var bombTimeLeft;
                    // Not yet defused? Count down!
                    if (this.bombDefuseTime === -1) {
                        bombTimeLeft = Math.round(this.bombExplodeTime-time/1000 + this.bombPlantTime);
                    }
                    // The bomb has been defused. Stay on the current time
                    else {
                        bombTimeLeft = Math.round(this.bombDefuseTime - this.bombPlantTime);
                    }
                    if (bombTimeLeft < 0) {
                        bombTimeLeft = 0;
                    }
                    this.ctx.fillText("" + bombTimeLeft, this.bombPosition[0]-4*this.scaling, this.bombPosition[1]-15*this.scaling);          
                  }
                  this.ctx.restore();
                }
                
                
                this.ctx.font = Math.round(10*this.scaling) + "pt Verdana"; // Set this for the player names
                for (i=0; i<this.players.length; i++)
                {
                    // Make sure we're in sync with the other messages..
                    // Delete older frames
                    while (this.players[i].positions.length > 0 && (time - this.players[i].positions[0].time) > 2000)
                    {
                      this.players[i].positions.splice(0,1);
                    }
                    
                    // There is no coordinate for this player yet
                    if (this.players[i].positions.length === 0) {
                        //debug("No co-ords for player idx " + i);
                        continue;
                    }
                    
                    this.ctx.save();
                    
                    if (this.players[i].team < 2) {
                        this.ctx.fillStyle = "black";
                    } else if (this.players[i].team === 2) {
                        if (this.players[i].positions[0].diedhere === false) {
                            this.ctx.fillStyle = "red";
                        }
                        else {
                            this.ctx.fillStyle = "rgba(255,0,0,0.3)";
                        }
                    } else if (this.players[i].team === 3) {
                        if (this.players[i].positions[0].diedhere === false) {
                            this.ctx.fillStyle = "blue";
                        }
                        else {
                            this.ctx.fillStyle = "rgba(0,0,255,0.3)";
                        }
                    }
                    
                    // Teleport directly to new spawn, if he died at this position
                    if (this.players[i].positions[0].diedhere)
                    {
                        if (this.players[i].positions[1])
                        {
                            //if (time >= this.players[i].positions[1].time)
                                this.players[i].positions.splice(0,1);
                        }
                    }
                    // Move the player smoothly towards the new position (interpolate)
                    else if (this.players[i].positions.length > 1)
                    {
                        if (this.players[i].positions[0].x === this.players[i].positions[1].x && this.players[i].positions[0].y === this.players[i].positions[1].y)
                        {
                            //if (time >= this.players[i].positions[1].time)
                                this.players[i].positions.splice(0,1);
                        }
                        else
                        {
                            // This function is called 20x a second
                            if (this.players[i].positions[0].swapx === null)
                            {
                                this.players[i].positions[0].swapx = this.players[i].positions[0].x > this.players[i].positions[1].x?-1:1;
                                this.players[i].positions[0].swapy = this.players[i].positions[0].y > this.players[i].positions[1].y?-1:1;
                            }
                            if (this.players[i].positions[0].diffx === null)
                            {
                                var timediff = this.players[i].positions[1].time - this.players[i].positions[0].time;
                                this.players[i].positions[0].diffx = Math.abs(this.players[i].positions[1].x - this.players[i].positions[0].x)/(timediff/50);
                                this.players[i].positions[0].diffy = Math.abs(this.players[i].positions[1].y - this.players[i].positions[0].y)/(timediff/50);
                            }
                            
                            var x = this.players[i].positions[0].x + this.players[i].positions[0].swapx*this.players[i].positions[0].diffx;
                            var y = this.players[i].positions[0].y + this.players[i].positions[0].swapy*this.players[i].positions[0].diffy;
                            
                            // We're moving too far...
                            if ((this.players[i].positions[0].swapx===-1 && x <= this.players[i].positions[1].x) || (this.players[i].positions[0].swapx===1 && x >= this.players[i].positions[1].x) || (this.players[i].positions[0].swapy===-1 && y <= this.players[i].positions[1].y) || (this.players[i].positions[0].swapy===1 && y >= this.players[i].positions[1].y))
                            {
                                this.players[i].positions.splice(0,1);
                            }
                            else
                            {
                                this.players[i].positions[0].x = x;
                                this.players[i].positions[0].y = y;
                            }
                        }
                    }
                    
                    var playerRadius = this.playerRadius;
                    // User hovers his mouse over this player
                    if (this.players[i].hovered || this.players[i].selected)
                    {
                        playerRadius = this.playerRadius + 4*this.scaling;
                        this.ctx.save();
                        this.ctx.beginPath();
                        this.ctx.fillStyle = "rgba(255, 255, 255, 0.8)";
                        this.ctx.arc(this.players[i].positions[0].x, this.players[i].positions[0].y, playerRadius + 2*this.scaling, 0, Math.PI*2, true);
                        this.ctx.fill();
                        this.ctx.restore();
                    }

                    // Draw player itself
                    this.ctx.beginPath();
                    this.ctx.arc(this.players[i].positions[0].x, this.players[i].positions[0].y, playerRadius, 0, Math.PI*2, true);
                    this.ctx.fill();
                    
                    // He got hurt this frame
                    if (this.players[i].positions[0].hurt)
                    {
                        this.ctx.strokeStyle = "rgb(230, 149, 0)";
                        this.ctx.beginPath();
                        this.ctx.arc(this.players[i].positions[0].x, this.players[i].positions[0].y, playerRadius, 0, Math.PI*2, true);
                        this.ctx.stroke();
                    }
                    
                    //if ($("#names").attr('checked'))
                    //if (this.shownames)
                    if ($("#stv_nametoggle").attr("checked"))
                    {
                        this.ctx.save();
                        var nameWidth = this.ctx.measureText(this.players[i].name).width;
                        this.ctx.translate(this.players[i].positions[0].x-(nameWidth/2), this.players[i].positions[0].y-(bShowHealthBar?16:10)*this.scaling);
                        this.ctx.fillText(this.players[i].name, 0, 0);
                        this.ctx.restore();
                    }
                    
                    // Draw view angle as white dot
                    this.ctx.translate(this.players[i].positions[0].x, this.players[i].positions[0].y);
                    this.ctx.fillStyle = "white";
                    this.ctx.rotate(this.players[i].positions[0].angle);
                    this.ctx.beginPath();
                    this.ctx.arc(0, Math.round(3 * this.scaling), Math.round(2 * this.scaling), 0, Math.PI*2, true);
                    this.ctx.fill();
                    
                    this.ctx.restore();

                    // Display player names above their heads
                    var bShowHealthBar = (this.players[i].health > 0 && $("#healthbars").attr('checked'));
                    // Draw health bars
                    if (bShowHealthBar)
                    {
                        this.ctx.save();
                        this.ctx.translate(this.players[i].positions[0].x-12*this.scaling, this.players[i].positions[0].y-12*this.scaling);
                        this.ctx.beginPath();
                        this.ctx.strokeStyle = "rgba(0, 0, 0, 0.7)";
                        this.ctx.rect(0, 0, 24*this.scaling, 4*this.scaling);
                        this.ctx.stroke();
                        
                        var width = (24*this.players[i].health/100)*this.scaling;
                        if (width > 0)
                        {
                            this.ctx.beginPath();
                            
                            if (this.players[i].health >= 70) {
                                this.ctx.fillStyle = "rgba(0, 255, 0, 0.7)";
                            }
                            else if (this.players[i].health >= 30) {
                                this.ctx.fillStyle = "rgba(255, 255, 50, 0.7)";
                            }
                            else {
                                this.ctx.fillStyle = "rgba(255, 0, 0, 0.7)";
                            }
                            
                            this.ctx.rect(0, 0, width, 4*this.scaling);
                            this.ctx.fill();
                        }
                        
                        this.ctx.restore();
                    }
                }
                
                // Draw the round end info box
                if (this.roundEnded !== -1)
                {
                    this.ctx.save();
                    this.ctx.font = Math.round(32*this.scaling) + "pt Verdana";

                    var winnertext = this.team[this.roundEnded] + " won the round!";
                    
                    // Draw a box around it
                    this.ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
                    this.ctx.beginPath();
                    this.ctx.rect(this.width/2-this.ctx.measureText(winnertext).width/2-5, this.height/2*this.scaling-34, this.ctx.measureText(winnertext).width + 10, 40);
                    this.ctx.fill();
                    
                    this.ctx.fillStyle = "rgb(255,255,255)";
                    this.ctx.fillText(winnertext, this.width/2-this.ctx.measureText(winnertext).width/2, this.height/2*this.scaling);
                    
                    this.ctx.restore();
                }
                
                // Draw the round time
                if (this.game === "cstrike" && this.mp_roundtime > 0 && this.roundStartTime > 0)
                {
                    this.ctx.save();
                    this.ctx.font = Math.round(14*this.scaling) + "pt Verdana";
                    this.ctx.fillStyle = "rgb(255,255,255)";
                    var timeleft = 0;
                    // Stop the counting on round end
                    if (this.roundEndTime > 0)
                    {
                        timeleft = this.mp_roundtime - this.roundEndTime + this.roundStartTime;
                    }
                    else
                    {
                        d = new Date();
                        timeleft = this.mp_roundtime - Math.floor(d.getTime()/1000) + this.roundStartTime;
                    }
                    if (timeleft < 0) {
                        timeleft = 0;
                    }

                    var timetext = "Timeleft: ";
                    var minutes = Math.floor(timeleft/60);
                    if (minutes < 10) {
                        timetext += "0";
                    }
                    timetext += minutes + ":";
                    var seconds = (timeleft%60);
                    if (seconds < 10) {
                        timetext += "0";
                    }
                    timetext += seconds;
                    this.ctx.fillText(timetext, this.width-this.ctx.measureText(timetext).width-50*this.scaling, this.height-50*this.scaling);
                    
                    this.ctx.restore();
                }
                
                // Draw the scoreboard
                if (this.spacebarPressed)
                {
                    this.ctx.save();
                    this.ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
                    this.ctx.strokeStyle = "rgb(255,165,0)";
                    this.ctx.translate(this.width*0.1, this.height*0.1);
                    
                    // Box with border
                    this.ctx.beginPath();
                    this.ctx.rect(0, 0, this.width*0.8, this.height*0.8);
                    this.ctx.fill();
                    this.ctx.beginPath();
                    this.ctx.rect(0, 0, this.width*0.8, this.height*0.8);
                    this.ctx.stroke();
                    
                    this.ctx.translate(10*this.scaling, 0);
                    
                    // Map and servername
                    this.ctx.font = Math.round(12*this.scaling) + "pt Verdana";
                    this.ctx.fillStyle = "rgba(255,165,0,0.9)";
                    this.ctx.fillText("Server: " + this.servername + " (" + this.map + ")", 0, 30*this.scaling);
                    
                    // Blue team header box
                    this.ctx.beginPath();
                    this.ctx.fillStyle = "rgba(69, 171, 255, 0.7)";
                    this.ctx.rect(0, 50*this.scaling, (this.width*0.8)/2-10*this.scaling, 80*this.scaling);
                    this.ctx.fill();
                    this.ctx.beginPath();
                    this.ctx.strokeStyle = "rgba(255, 255, 255, 0.7)";
                    this.ctx.rect(0, 50*this.scaling, (this.width*0.8)/2-10*this.scaling, 80*this.scaling);
                    this.ctx.stroke();
                    
                    this.ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
                    this.ctx.font = Math.round(18*this.scaling) + "pt Verdana";
                    // Team name
                    this.ctx.fillText(this.team[3], 10*this.scaling, 90*this.scaling);
                    
                    // Player count in team
                    this.ctx.font = Math.round(14*this.scaling) + "pt Verdana";
                    this.ctx.fillText(this.teamPlayersAlive[1] + "/" + this.teamPlayerAmount[2] + " players alive", 16*this.scaling, 120*this.scaling);
                    
                    // Team points
                    this.ctx.font = Math.round(36*this.scaling) + "pt Verdana";
                    this.ctx.fillText(this.teamPoints[1] + "", (this.width*0.8)/2-16*this.scaling-this.ctx.measureText(this.teamPoints[1] + "").width, 120*this.scaling);
                    
                    // Table header
                    this.ctx.fillStyle = "rgba(69, 171, 255, 0.9)";
                    this.ctx.font = Math.round(10*this.scaling) + "pt Verdana";
                    this.ctx.fillText("Player", 10*this.scaling, 150*this.scaling);       
                    
                    //to position these, get the centre line of the scoreboard (sourcetv.width*0.8/2) and then substract the width of the other columns preceding 
                    //the one you want placed. all headers have the same Y positions (150*scaling)
                    deathWidth = this.ctx.measureText("Deaths").width;
                    this.ctx.fillText("Deaths", (this.width*0.8)/2 - 20*this.scaling - deathWidth, 150*this.scaling);
                    
                    fragsWidth = this.ctx.measureText("Frags").width;
                    this.ctx.fillText("Frags", (this.width*0.8)/2 - 28*this.scaling - deathWidth - fragsWidth, 150*this.scaling);
                    
                    classWidth = this.ctx.measureText("Class").width;
                    this.ctx.fillText("Class", (this.width*0.8)/2 - 160*this.scaling - deathWidth - fragsWidth - classWidth, 150*this.scaling);
                    
                    
                    // Player list border
                    this.ctx.strokeStyle = "rgba(69, 171, 255, 0.9)";
                    this.ctx.beginPath();
                    iListBorderHeight = this.height*0.8-200*this.scaling;
                    this.ctx.rect(0, 160*this.scaling, (this.width*0.8)/2-10*this.scaling, iListBorderHeight);
                    this.ctx.stroke();
                    
                    // Player list
                    this.ctx.font = Math.round(14*this.scaling) + "pt Verdana";
                    iOffset = 0;
                    for (i=0; i<this.players.length; i++)
                    {
                        if (this.players[i].team !== 3) {
                            continue;
                        }
                        
                        iHeight = (180 + 20*iOffset)*this.scaling;
                        if (iHeight > iListBorderHeight) {
                            break;
                        }
                        
                        if (this.players[i].alive) {
                            this.ctx.fillStyle = "rgba(69, 171, 255, 0.9)";
                        }
                        else {
                            this.ctx.fillStyle = "rgba(69, 171, 255, 0.6)";
                        }
                        
                        //likewise for the headers, get centre pos and subtract
                        
                        this.ctx.fillText(this.players[i].name, 10*this.scaling, iHeight);
                        this.ctx.fillText(this.players[i].deaths, (this.width*0.8)/2 - 20*this.scaling - deathWidth, iHeight);
                        this.ctx.fillText(this.players[i].frags, (this.width*0.8)/2 - 28*this.scaling - deathWidth - fragsWidth, iHeight);
                        
                        //player classes are a bit diff, since they're numbered and we want them in name
                        classname = this.classnames[this.players[i].pclass];
                        this.ctx.fillText(classname, (this.width*0.8)/2 - 160*this.scaling - deathWidth - fragsWidth - classWidth, iHeight);
                        
                        
                        if (this.players[i].has_intel) {
                            this.ctx.fillText("F", (this.width*0.8)/2 - 66*this.scaling - deathWidth - fragsWidth - classWidth, iHeight);
                        }
                        iOffset += 1;
                    }
                    
                    // Red team!
                    this.ctx.save();
                    this.ctx.translate((this.width*0.8)/2, 0);
                    
                    // Red team header box
                    this.ctx.beginPath();
                    this.ctx.fillStyle = "rgba(207, 68, 102, 0.7)";
                    this.ctx.rect(0, 50*this.scaling, (this.width*0.8)/2-20*this.scaling, 80*this.scaling);
                    this.ctx.fill();
                    this.ctx.beginPath();
                    this.ctx.strokeStyle = "rgba(255, 255, 255, 0.7)";
                    this.ctx.rect(0, 50*this.scaling, (this.width*0.8)/2-20*this.scaling, 80*this.scaling);
                    this.ctx.stroke();
                    
                    this.ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
                    this.ctx.font = Math.round(18*this.scaling) + "pt Verdana";
                    // Team name
                    this.ctx.fillText(this.team[2], (this.width*0.8)/2-31*this.scaling-this.ctx.measureText(this.team[2]).width, 90*this.scaling);
                    
                    // Player count in team
                    this.ctx.font = Math.round(14*this.scaling) + "pt Verdana";
                    var sBuf = "players alive " + this.teamPlayersAlive[0] + "/" + this.teamPlayerAmount[1];
                    this.ctx.fillText(sBuf, (this.width*0.8)/2-37*this.scaling-this.ctx.measureText(sBuf).width, 120*this.scaling);
                    
                    // Team points
                    this.ctx.font = Math.round(36*this.scaling) + "pt Verdana";
                    this.ctx.fillText(this.teamPoints[0] + "", 5*this.scaling, 120*this.scaling);
                    
                    // Table header
                    this.ctx.fillStyle = "rgba(207, 68, 102, 0.9)";
                    this.ctx.font = Math.round(10*this.scaling) + "pt Verdana";
                    this.ctx.fillText("Player", 10*this.scaling, 150*this.scaling);
                    
                    deathWidth = this.ctx.measureText("Deaths").width;
                    this.ctx.fillText("Deaths", (this.width*0.8)/2-30*this.scaling-deathWidth, 150*this.scaling);
                    
                    fragsWidth = this.ctx.measureText("Frags").width;
                    this.ctx.fillText("Frags", (this.width*0.8)/2-38*this.scaling-deathWidth-fragsWidth, 150*this.scaling);
                    
                    classWidth = this.ctx.measureText("Class").width;
                    this.ctx.fillText("Class", (this.width*0.8)/2 - 180*this.scaling - deathWidth - fragsWidth - classWidth, 150*this.scaling);
                    
                    // Player list border
                    this.ctx.strokeStyle = "rgba(207, 68, 102, 0.9)";
                    this.ctx.beginPath();
                    iListBorderHeight = this.height*0.8-200*this.scaling;
                    this.ctx.rect(0, 160*this.scaling, (this.width*0.8)/2-20*this.scaling, iListBorderHeight);
                    this.ctx.stroke();
                    
                    // Player list
                    this.ctx.font = Math.round(14*this.scaling) + "pt Verdana";
                    iOffset = 0;
                    for (i=0; i<this.players.length; i++)
                    {
                        if (this.players[i].team !== 2) {
                            continue;
                        }
                        
                        iHeight = (180 + 20*iOffset)*this.scaling;
                        if (iHeight > iListBorderHeight) {
                            break;
                        }
                        
                        if (this.players[i].alive) {
                            this.ctx.fillStyle = "rgba(207, 68, 102, 0.9)";
                        }
                        else {
                            this.ctx.fillStyle = "rgba(207, 68, 102, 0.6)";
                        }
                        
                        this.ctx.fillText(this.players[i].name, 10*this.scaling, iHeight);
                        this.ctx.fillText(this.players[i].deaths, (this.width*0.8)/2 - 20*this.scaling - deathWidth, iHeight);
                        this.ctx.fillText(this.players[i].frags, (this.width*0.8)/2 - 28*this.scaling - deathWidth - fragsWidth, iHeight);
                        
                        classname = this.classnames[this.players[i].pclass];
                        this.ctx.fillText(classname, (this.width*0.8)/2 - 160*this.scaling - deathWidth - fragsWidth - classWidth, iHeight);
                        
                        if (this.players[i].has_intel) {
                            this.ctx.fillText("F", (this.width*0.8) / 2 - 66*this.scaling - deathWidth - fragsWidth, iHeight);
                        }

                        iOffset += 1;
                    }
                    
                    this.ctx.restore();
                    
                    // Spectators
                    iOffset = 10*this.scaling + this.ctx.measureText(this.teamPlayerAmount[0] + " Spectators: ").width;
                    iListBorderHeight += 185*this.scaling;
                    this.ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
                    this.ctx.fillText(this.teamPlayerAmount[0] + " Spectators: ", 10*this.scaling, iListBorderHeight);
                    var bMoreSpectators = false;
                    for (i=0; i<this.players.length; i++)
                    {
                        if (this.players[i].team > 1) {
                            continue;
                        }
                        
                        this.ctx.fillText((bMoreSpectators?", ":" ") + this.players[i].name, iOffset, iListBorderHeight);
                        iOffset += this.ctx.measureText((bMoreSpectators?", ":" ") + this.players[i].name).width;
                        bMoreSpectators = true;
                    }
                    
                    this.ctx.restore();
                }
            }
            catch(ex) {
                this.debug('Error: ' + ex);
            }
        },

        loadMapImageInfo : function(game, map) {
            // Load the background map image
            this.background = new Image();
            $(this.background).load(function() {
                this.canvas = document.createElement('canvas');

                // Browser does not support canvas
                if (!this.canvas.getContext)
                {
                  $("#sourcetv2d").html("<h2>Your browser does not support the canvas element.</h2>");
                  this.disconnect();
                  return;
                }

                //this.scaling = 1.0;

                this.playerRadius = Math.round(5 * this.scaling);
                this.width = this.background.width * this.scaling;
                this.height = this.background.height * this.scaling;
                this.canvas.setAttribute('width',this.width);  
                this.canvas.setAttribute('height',this.height);

                $("#sourcetv2d").append(this.canvas);
                $("#sourcetv2d").mousemove(function (ev) { this.mouseMove(ev); });
                $("#sourcetv2d").click(function (ev) { this.mouseClick(ev); });

                this.ctx = this.canvas.getContext('2d');
                this.ctx.drawImage(this.background,0,0,this.width,this.height);

                // Get the map config
                $.ajax({
                  type: 'GET',
                  url: '/maps/' + game + '/' + map + '.txt',
                  dataType: 'json',
                  success: function (json) {
                      this.mapsettings.xoffset = json.xoffset;
                      this.mapsettings.yoffset = json.yoffset;
                      this.mapsettings.flipx = json.flipx;
                      this.mapsettings.flipy = json.flipy;
                      this.mapsettings.scale = json.scale;
                      this.mapsettingsLoaded = true;
                  },
                  error: function (jqXHR, textStatus) {
                      alert("Failed to load map info: " + jqXHR + " " + textStatus);
                      this.mapsettingsFailed = true;
                  }
                });
            }).error(function () {
                this.canvas = document.createElement('canvas');

                // Browser does not support canvas
                if (!this.canvas.getContext)
                {
                  $("#sourcetv2d").html("<h2>Your browser does not support the canvas element.</h2>");
                  return;
                }

                //this.scaling = 1.0;

                // Default height
                this.width = 1280 * this.scaling;
                this.height = 1024 * this.scaling;
                this.canvas.setAttribute('width',this.width);
                this.canvas.setAttribute('height',this.height);

                $("#sourcetv2d").append(this.canvas);

                this.ctx = this.canvas.getContext('2d');
                this.background = null;
          }).attr('src', '/maps/' + this.game + '/' + this.map + '.jpg');
        },

        sortScoreboard : function() {
            this.players.sort(function (a,b) {
                if (a.frags === b.frags) {
                    return a.deaths - b.deaths;
                }
                return b.frags - a.frags;
            });
        },

        getPlayerAtPosition : function(x, y) {
            for (var i=0;i<this.players.length;i++)
            {
                if (this.players[i].positions[0])
                {
                    if ((this.players[i].positions[0].x + this.playerRadius*2) >= x && this.players[i].positions[0].x <= x && (this.players[i].positions[0].y + this.playerRadius) >= y && (this.players[i].positions[0].y - this.playerRadius) <= y)
                    {
                        return i;
                    }
                }
            }
            return -1;
        },

        mouseMove : function(e) {
            if (this.socket===null || this.players.length === 0) {
                return;
            }
                
            var offs = $("#sourcetv2d").offset();
            var x = e.pageX-offs.left-$("#playerlist-container").width();
            if (x < 0 || x > this.width) {
                return;
            }
            
            var y = e.pageY-offs.top;
            
            for (var i=0;i<this.players.length;i++)
            {
                this.players[i].hovered = false;
            }
            
            $("#player").text("");
            
            var player = this.getPlayerAtPosition(x, y);
            if (player !== -1)
            {
                $("#player").html("Target: <b>" + this.players[player].name + "</b>");
                this.players[player].hovered = true;
                return;
            }
        },

        mouseClick : function(e) {
            if (this.socket===null || this.players.length === 0) {
                return;
            }
            
            var offs = $("#sourcetv2d").offset();
            var x = e.pageX-offs.left-$("#playerlist-container").width();
            if (x < 0 || x > this.width) {
                return;
            }
            
            var y = e.pageY-offs.top;
            
            for (var i=0;i<this.players.length;i++)
            {
                this.players[i].selected = false;
                $("#usrid_" + this.players[i].userid).removeClass("selected");
            }
            $("#selectedplayer").text("");
            
            var player = this.getPlayerAtPosition(x, y);
            if (player !== -1)
            {
                $("#usrid_" + this.players[player].userid).addClass("selected");
                $("#selectedplayer").html("Selected: <b>" + this.players[player].name + "</b>");
                this.players[player].selected = true;
                return;
            }
        },

        selectPlayer : function(userid) {
            for (var i=0;i<this.players.length;i++)
            {
                if (this.players[i].team > 1 && this.players[i].userid === userid)
                {
                    for (var x=0;x<this.players.length;x++)
                    {
                        this.players[x].selected = false;
                        $("#usrid_" + this.players[x].userid).removeClass("selected");
                    }
                    this.players[i].selected = true;
                    $("#usrid_" + this.players[i].userid).addClass("selected");
                    $("#selectedplayer").html("Selected: <b>" + this.players[i].name + "</b>");
                    break;
                }
            }
        },

        highlightPlayer : function(userid) {
            for (var i=0;i<this.players.length;i++)
            {
                if (this.players[i].team > 1 && this.players[i].userid === userid)
                {
                    for (var x=0;x<this.players.length;x++)
                    {
                        this.players[x].hovered = false;
                    }
                    this.players[i].hovered = true;
                    $("#player").html("Target: <b>" + this.players[i].name + "</b>");
                    break;
                }
            }
        },

        unHighlightPlayer : function(userid) {
            for (var i=0;i<this.players.length;i++)
            {
                if (this.players[i].team > 1 && this.players[i].userid === userid)
                {
                    this.players[i].hovered = false;
                    $("#player").text("");
                    break;
                }
            }
        },

        debugPlayers : function() {
            // {'userid': parseInt(frame.userid), 'ip': frame.ip, 'name': frame.name, 'team': parseInt(frame.team), 'positions': [], 'alive': true};
            for (var i=0;i<this.players.length;i++)
            {
                this.debug(i + ": #" + this.players[i].userid + ", Name: " + this.players[i].name + ", IP: " + this.players[i].ip + ", Team: " + this.players[i].team + ", Alive: " + this.players[i].alive + ", Positions: " + this.players[i].positions.length);
                if (this.players[i].positions.length > 0) {
                    this.debug(i + ": 1x: " + this.players[i].positions[0].x + ", 1y: " + this.players[i].positions[0].y + ", 1diffx: " + this.players[i].positions[0].diffx + ", 1diffy: " + this.players[i].positions[0].diffy + ", 1swapx: " + this.players[i].positions[0].swapx + ", 1swapy: " + this.players[i].positions[0].swapy + ", diedhere: " + this.players[i].positions[0].diedhere);
                }
                if (this.players[i].positions.length > 1) {
                    this.debug(i + ": 2x: " + this.players[i].positions[1].x + ", 2y: " + this.players[i].positions[1].y + ", 2diffx: " + this.players[i].positions[1].diffx + ", 2diffy: " + this.players[i].positions[1].diffy + ", 2swapx: " + this.players[i].positions[1].swapx + ", 2swapy: " + this.players[i].positions[1].swapy + ", diedhere: " + this.players[i].positions[1].diedhere);
                }
            }

            this.debug("");
        },

        sendChatMessage : function() {
            var d, timestring;
            if (this.socket===null) {
                return;
            }

            if ($("#chatinput").val() === "") {
                return;
            }

            if ($("#chatnick").val() === "")
            {
                alert("You have to enter a nickname first.");
                return;
            }

            this.socket.send($("#chatnick").val() + ": " + $("#chatinput").val());
            d = new Date();
            timestring = "(";
            if (d.getHours() < 10) {
                timestring += "0";
            }
            timestring += d.getHours() + ":";
            
            if (d.getMinutes() < 10) {
                timestring += "0";
            }
            timestring += d.getMinutes() + ":";

            if (d.getSeconds() < 10) {
                timestring += "0";
            }

            timestring += d.getSeconds() + ") ";

            $("#chatoutput").append(document.createTextNode(timestring + $("#chatnick").val() + ": " + $("#chatinput").val()));
            $("#chatoutput").append("<br />");
            $('#chatoutput').prop('scrollTop', $('#chatoutput').prop('scrollHeight'));

            $("#chatinput").val("");
            $("#chatinput").focus();
        },

        toggleNames : function() {
            if (this.shownames) {
                this.shownames = false;
            } else {
                this.shownames = true;
            }
        },

        debug : function(msg) {
            $("#debug").html($("#debug").html() + "<br>" + msg);
        }
    };
}());

$(document).keydown(function (e) {
    "use strict";
    if (($(document.activeElement).attr("id") !== "chatinput") && ($(document.activeElement).attr("id") !== "chatnick") && (e.which === 32)) {
        SourceTV2D.spacebarPressed = true;
        return false;
    }
});
$(document).keyup(function (e) {
    "use strict";
    if ($(document.activeElement).attr("id") !== "chatinput" && $(document.activeElement).attr("id") !== "chatnick" && e.which === 32) {
        SourceTV2D.spacebarPressed = false;
        return false;
    }
});