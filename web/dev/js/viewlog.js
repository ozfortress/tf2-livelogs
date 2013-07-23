/* js used to modify tables and what not inside the log view page
 * will probably also contain stuff for real-time display
 */
 
$(document).ready(function()
{
    "use strict";
    var stat_table = $('#general_stats').dataTable( {
        "aaSorting": [[1, 'desc']],
        "aoColumnDefs": [
            { "sType": "html", "bSearchable": false, "aTargets": [0] },
            { "sType": "numeric", "bSearchable": false, "aTargets": ["_all"] },
            { "asSorting": [ "desc", "asc" ], "aTargets": [ "_all" ] }
        ],
        "bPaginate": false,
        "bAutoWidth": false,
        "bSortClasses": false,
        "bSearchable": false,
        "bInfo": false,
        "bJQueryUI": false,
        "bUseRendered": true,
        "bFilter": false
    });

    var team_stats = $('#team_stats').dataTable( {
        "aaSorting": [[1, 'desc']],
        "aoColumnDefs": [
            { "sType": "html", "bSearchable": false, "aTargets": [0] },
            { "sType": "numeric", "bSearchable": false, "aTargets": ["_all"] },
            { "asSorting": [ "desc", "asc" ], "aTargets": [ "_all" ] }
        ],
        "bPaginate": false,
        "bAutoWidth": false,
        "bSortClasses": false,
        "bSearchable": false,
        "bInfo": false,
        "bJQueryUI": false,
        "bUseRendered": true,
        "bFilter": false
    });

    var medic_stats = $('#medic_stats').dataTable( {
        "aaSorting": [[1, 'desc']],
        "aoColumnDefs": [
            { "sType": "html", "bSearchable": false, "aTargets": [0] },
            { "sType": "numeric", "bSearchable": false, "aTargets": ["_all"] },
            { "asSorting": [ "desc", "asc" ], "aTargets": [ "_all" ] }
        ],
        "bPaginate": false,
        "bAutoWidth": false,
        "bSortClasses": false,
        "bSearchable": false,
        "bInfo": false,
        "bJQueryUI": false,
        "bUseRendered": true,
        "bFilter": false
    });

});

jQuery.fn.dataTableExt.oSort['dt-numeric-html-asc'] = function(a,b) {
    "use strict";
    var x = a.replace( /<.*?>/g, "" ), y = b.replace( /<.*?>/g, "" );
    x = parseFloat( x );
    y = parseFloat( y );
    return ((x < y) ? -1 : ((x > y) ? 1 : 0));
};

jQuery.fn.dataTableExt.oSort['dt-numeric-html-desc'] = function(a,b) {
    "use strict";
    var x = a.replace( /<.*?>/g, "" ), y = b.replace( /<.*?>/g, "" );
    x = parseFloat( x );
    y = parseFloat( y );
    return ((x < y) ? 1 : ((x > y) ? -1 : 0));
};

var llWSClient = llWSClient || (function() {
    "use strict";
    var client, ws, connect_msg = {}, HAD_FIRST_UPDATE = false, auto_update = true, time_elapsed_sec, client_index = []; //our client socket and message that will be sent on connect, containing the log id

    return {
        init : function(ip, port, log_id) {
            ws = "ws://" + ip + ":" + port + "/logupdate";
            
            console.log("WS URI: %s", ws);
            
            connect_msg.ident = log_id;
            
            this.clientConnect(ws);
        },
        
        clientConnect : function(ws_uri) {
            try {
                if (window.WebSocket) {
                    client = new WebSocket(ws_uri);
                    client.onmessage = function(msg) { llWSClient.onMessage(msg); };
                    client.onopen = function(event) { llWSClient.onOpen(event); };
                    client.onclose = function(event) { llWSClient.onClose(event); };
                    client.onerror = function(event) { llWSClient.onError(event); };
                }
                else {
                    console.log("Websockets not supported");
                }
            }
            catch (error) {
                console.log("Had error trying to establish websocket: %s", error);
                return;
            }
        },
        
        onOpen : function(event) {
            console.log("Client websock opened. Sending connect message. Event: %s", event.data);
            client.send(JSON.stringify(connect_msg));
        },
        
        onClose : function(event) {
            console.log("Client websocket closed: %s", event);
            client = null;
        },
        
        onError : function(event) {
            console.log("Had WS error: %s", event);
        },
        
        onMessage : function(msg) {
            var msg_data = msg.data, update_json, element;
            console.log("MESSAGE: " + msg_data);
            
            if (msg_data === "LOG_NOT_LIVE") {
                console.log("Log not live. Closing connection");
                //server will close client

            } else if (!auto_update) {
                return;
                
            } else if (msg_data === "LOG_IS_LIVE") {
                HAD_FIRST_UPDATE = false;

            } else if (msg_data === "LOG_END") {
                //update status element with "Complete"

                element = document.getElementById("log_status_span");

                if ($("#log_status_span").hasClass("text-success")) { //if it has the text-success class, remove it and add text-error (red)
                    $("#log_status_span").removeClass("text-success");

                    $("#log_status_span").addClass("text-error");
                }

                element.innerHTML = "Complete"; 

            } else {
                //all other messages are json encoded packets

                try {
                    update_json = jQuery.parseJSON(msg_data);
                }
                catch (exception) {
                    console.log("Error trying to decode or parse json. Message: %s, ERROR: %s", msg_data, exception);
                    return;
                }
                
                //update_json may contain any of the following structures:
                //first structure: [{"time": "unix timestamp"}] - the timestamp will be the time between the start and current log time
                //second structure: [{"score": [{"red": val}, {"blue": val}]}]
                //third structure: [{"chat": [{"name": {{"message": msg}, {"msg_type": team/all}, {"team": team colour}}}, repeat]}]
                //fourth structure: a stat object: [{"stat" : [{"sid": [{"type": val}, ...], {"sid": .....}, repeat]}]
                //fifth: team stats (red/blue): [{"team_stat": {"team": [{"stat": val}, ...], {"team": [{ "stat": val, ...}, ...]}]

                if (update_json.gametime !== undefined) {
                    this.parseTimeUpdate(update_json.gametime);
                }

                if (update_json.score !== undefined) {
                    this.parseScoreUpdate(update_json.score);
                }

                if (update_json.chat !== undefined) {
                    this.parseChatUpdate(update_json.chat);
                }

                if (update_json.stat !== undefined) {
                    this.parseStatUpdate(update_json.stat);
                }

                if (update_json.team_stat !== undefined) {
                    this.parseTeamStatUpdate(update_json.team_stat);
                }

                if (!HAD_FIRST_UPDATE) {
                    HAD_FIRST_UPDATE = true;
                }
            }
        },

        parseTimeUpdate : function(timestamp) {
            //update the time. requires use of sprintf
            time_elapsed_sec = Number(timestamp);
            var new_time_disp;

            new_time_disp = sprintf("%02d minute(s) and %02d second(s)", (time_elapsed_sec/60)%60, time_elapsed_sec%60);

            console.log("Got timestamp message. Timestamp: %d Time display: %s", time_elapsed_sec, new_time_disp);


            document.getElementById("time_elapsed").innerHTML = new_time_disp;
        },

        parseScoreUpdate : function (score_obj) {
            var red_score = 0, blue_score = 0, red_element, blue_element;

            if (score_obj.red !== undefined) {
                red_score = Number(score_obj.red);
            }
            if (score_obj.blue !== undefined) {
                blue_score = Number(score_obj.blue);
            }

            console.log("SCORE UPDATE. RED: +%d BLUE: +%d", red_score, blue_score);
            if (!HAD_FIRST_UPDATE) {
                document.getElementById("red_score_value").innerHTML = red_score;
                document.getElementById("blue_score_value").innerHTML = blue_score;

            } else { //it's a delta compressed score update
                if (red_score) {
                    red_element = document.getElementById("red_score_value");
                    if (red_element) {
                        red_element.innerHTML = Number(red_element.innerHTML) + red_score;
                    }
                }
                if (blue_score) {
                    blue_element = document.getElementById("blue_score_value");
                    if (blue_element) {
                        blue_element.innerHTML = Number(blue_element.innerHTML) + blue_score;
                    }
                }

            }
        },

        parseChatUpdate : function(chat_obj) {
            var chat_name, chat_team, chat_type, chat_message, team_class;
            //underneath "chat" is the player names and the message
            $.each(chat_obj, function(chat_id, chat_data) {
                //chat_data will be all the message shit
                chat_name = chat_data.name;
                chat_team = chat_data.team.toLowerCase();
                chat_type = chat_data.msg_type;
                chat_message = chat_data.msg;

                if (chat_team === "red") {
                    team_class = "red_player";
                } else if (chat_team === "blue") {
                    team_class = "blue_player";
                } else {
                    team_class = "no_team_player";
                }

                console.log("CHAT: player %s (team: %s) msg: (%s) %s", chat_name, chat_team, chat_type, chat_message);

                $("table#chat_table tbody").append(
                    '<tr>' +
                        '<td><span class="' + team_class + ' player_chat">' + chat_name + '</span></td>' +
                        '<td><span class="player_chat">(' + chat_type + ')</span> <span class="player_chat_message">' + chat_message + '</span></td>' +
                    '</tr>');
            });
        },
        
        parseStatUpdate : function(stat_obj) {
            try {
                var element, element_id, special_element_tags = ["kpd", "dpd", "dpr", "dpm"], i, tmp, num_rounds, deaths, damage, kills, tmp_result;
                num_rounds = Number(document.getElementById("red_score_value").innerHTML) + Number(document.getElementById("blue_score_value").innerHTML);
                
                $.each(stat_obj, function(sid, stats) {
                    //check if player exists on page already
                    if (document.getElementById(sid + ".name")) {
                        $.each(stats, function(stat, value) {
                            element_id = sid + "." + stat;
                
                            console.log("SID: %s, STAT: %s, VALUE: %s, HTML ELEMENT: %s", sid, stat, value, element_id);

                            var element = llWSClient.get_element_cache(sid, element_id);
                            
                            if (element) {
                                //console.log("Got element %s, VALUE: %s", element, element.innerHTML);
                                if (HAD_FIRST_UPDATE) {                    
                                    if (stat === "healing_done" || stat === "ubers_used" || stat === "ubers_lost") {
                                        llWSClient.updateTableCell("#medic_stats", element, Number(element.innerHTML) + Number(value));
                                    } else {
                                        llWSClient.updateTableCell("#general_stats", element, Number(element.innerHTML) + Number(value));
                                    }
                                } else {
                                    if (stat === "healing_done" || stat === "ubers_used" || stat === "ubers_lost") {
                                        llWSClient.updateTableCell("#medic_stats", element, Number(value));
                                    } else {
                                        llWSClient.updateTableCell("#general_stats", element, Number(value));
                                    }
                                }
                                
                                //console.log("Element new value: %s", element.innerHTML);
                            }
                        });
                        
                        /* now that we've looped through all the stats, we need to edit the combo columns like kpd, dpd and dpr */
                        for (i = 0; i < special_element_tags.length; i++) {
                            tmp = special_element_tags[i];
                            element_id = sid + "." + tmp;

                            element = llWSClient.get_element_cache(sid, element_id);
                            
                            //console.log("SID: %s, HTML ELEMENT: %s", sid, element_id);
                            
                            var death_element = llWSClient.get_element_cache(sid, sid + ".deaths"), damage_element = llWSClient.get_element_cache(sid, sid + ".damage_dealt");

                            if (!death_element || !damage_element) {
                                console.log("Unable to get death and or damage element for sid %s", sid);
                                continue;
                            }

                            deaths = Number(death_element.innerHTML);
                            damage = Number(damage_element.innerHTML);
                            
                            //multiply by 100 and div by 100 for 2 dec places rounding
                            if (element) {
                                if (tmp === "kpd") {
                                    var kill_element = llWSClient.get_element_cache(sid, sid + ".kills");
                                    kills = Number(kill_element.innerHTML);
                                    tmp_result = Math.round(kills / (deaths || 1) * 100) / 100;
                                } else if (tmp === "dpd") {
                                    tmp_result = Math.round(damage / (deaths || 1) * 100) / 100;
                                } else if (tmp === "dpr") {
                                    tmp_result = Math.round(damage / (num_rounds || 1) * 100) / 100;
                                } else if (tmp === "dpm") {
                                    tmp_result = Math.round(damage / (time_elapsed_sec/60 || 1) * 100) / 100;
                                } else {
                                    console.log("Invalid element %s in special element array", tmp);
                                    continue;
                                }

                                llWSClient.updateTableCell("#general_stats", element, tmp_result);
                            }
                        }
                    } else {
                        //this means the player needs to be added to the table, how do?
                        console.log("New player to be added. SID: %s", sid);
                    }
                });

                //now we re-draw the table, so sorting is updated with new values
                setTimeout(function() { llWSClient.redraw_table("#general_stats"); }, 3250);
                setTimeout(function() { llWSClient.redraw_table("#medic_stats"); }, 3250);
            }
            catch (exception) {
                console.log("Exception trying to parse stat update. Error: %s", exception);
            }
        },

        parseTeamStatUpdate : function(stat_obj) {
            try {
                var element, element_id, special_element_tags = ["dpm"], i, tmp, num_rounds, deaths, damage, kills, tmp_result;

                $.each(stat_obj, function(team, team_stat) {

                    $.each(team_stat, function(stat, value) {
                        element_id = team + "." + stat;

                        element = llWSClient.get_element_cache(team, element_id);

                        if (element) {
                            if (HAD_FIRST_UPDATE) {
                                /* we've had the first update, so we want to increment values here */
                                llWSClient.updateTableCell("#team_stats", element, Number(element.innerHTML) + Number(value));
                            }
                            else {
                                llWSClient.updateTableCell("#team_stats", element, Number(value));
                            }
                        }
                    });

                    for (i = 0; i < special_element_tags.length; i++) {
                        tmp = special_element_tags[i];
                        element_id = team + "." + tmp;

                        element = llWSClient.get_element_cache(team, element_id);

                        var damage_element = llWSClient.get_element_cache(team, team + ".team_damage_dealt");

                        if (!damage_element) {
                            continue;
                        }

                        damage = Number(damage_element.innerHTML);

                        if (element) {
                            if (tmp === "dpm") {
                                tmp_result = Math.round(damage / (time_elapsed_sec/60 || 1) * 100) / 100;
                            }

                            llWSClient.updateTableCell("#team_stats", element, tmp_result);
                        }
                    }
                });

                setTimeout(function() { llWSClient.redraw_table("#team_stats"); }, 3250);
            }
            catch (exception) {
                console.log("Exception trying to parse team stat update: %s", exception);
            }
        },

        highlight : function(element, highlight_colour) {
            highlight_colour = typeof highlight_colour !== 'undefined' ? highlight_colour : "#CCFF66";

            $(element).effect("highlight", {color: highlight_colour}, 3400);
        },
        
        toggleUpdate : function() {
            if (auto_update) {
                auto_update = false;
                
                if (client) {
                    client.close(200);
                }
                
            } else {
                auto_update = true;
                this.clientConnect(ws);
            }
        },

        updateTableCell : function(table_id, cell, new_value) {
            if (Number(cell.innerHTML) === new_value) {
                //don't update table cell if the values are the same
                return;
            }

            var table = $(table_id).dataTable();

            //cell_pos = [row index, col index (visible), col index (all)]
            var cell_pos = table.fnGetPosition(cell);


            //fnUpdate(data, row, column, bool:redraw, bool:do_pre-draw)
            table.fnUpdate(new_value, cell_pos[0], cell_pos[2], false, false); //updates cell values

            this.highlight(cell);
        },

        redraw_table : function(table_id) {
            var table = $(table_id).dataTable();
            table.fnDraw(true); //re-draws the table, resorting with updated cell values
                                //this should help significantly with performance issues in redrawing the table for every stat that has been changed
        },

        get_element_cache : function(sid, element_id) {
            //this function caches element objects, so they do not need to be retrieved for every stat update

            if (!(sid in client_index)) {
                //add the client sid to the element cache. the sid will contain an array of stats and their page elements
                client_index.sid = [];
            }

            var element = null;
            if (!(element_id in client_index.sid)) {
                element = document.getElementById(element_id);
                client_index.sid.element_id = element; //add the element to the client's element cache
            }
            else {
                element = client_index.sid.element_id;
            }

            //return the element
            return element;
        },

        addStatRow : function() {
            $("#general_stats").dataTable().fnAddData([
                    "row1",
                    "row2"
                ]);
        },
    };
}());

window.onbeforeunload = function() {
    "use strict";
    if (llWSClient.client) {
        llWSClient.client.close();
    }
};
