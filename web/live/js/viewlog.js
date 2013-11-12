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

var llWSClient = llWSClient || (function() {
    "use strict";

    //our client socket and message that will be sent on connect, containing the log id
    var client, ws, connect_msg = {}, HAD_FIRST_UPDATE = false, auto_update = true, time_elapsed_sec, client_index = [];

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
                } else {
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

                if (!element) {
                    return;
                }

                if ($(element).hasClass("text-success")) { //if it has the text-success class, remove it and add text-error (red)
                    $(element).removeClass("text-success");

                    $(element).addClass("text-error");
                }

                element.innerHTML = "Complete"; 

                /* we expect one last full update packet after this */
                HAD_FIRST_UPDATE = false; // so the parsing will set instead of increment

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

            red_element = llWSClient.get_element_cache("global", "red_score_value");
            blue_element = llWSClient.get_element_cache("global", "blue_score_value");

            if (!red_element || !blue_element) {
                console.log("ERROR: Unable to get score elements for both teams");
                return;
            }

            if (typeof score_obj.red !== 'undefined') {
                red_score = Number(score_obj.red);
            }
            if (typeof score_obj.blue !== 'undefined') {
                blue_score = Number(score_obj.blue);
            }

            console.log("SCORE UPDATE. RED: +%d BLUE: +%d", red_score, blue_score);

            if (!HAD_FIRST_UPDATE) {
                red_element.innerHTML = red_score;
                blue_element.innerHTML = blue_score;

            } else { //it's a delta compressed score update
                if (red_score) {
                    red_element.innerHTML = Number(red_element.innerHTML) + red_score;
                }
                if (blue_score) {
                    blue_element.innerHTML = Number(blue_element.innerHTML) + blue_score;
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

                team_class = llWSClient.get_name_class(chat_team);

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
                var element, element_id, med_element, name_class, name_element, classes, 
                special_element_tags = ["kpd", "dpd", "dpr", "dpm"], i, 
                tmp, num_rounds, deaths, damage, kills, tmp_result;

                num_rounds = Number(llWSClient.get_element_cache("global", "red_score_value").innerHTML) + Number(llWSClient.get_element_cache("global", "blue_score_value").innerHTML);

                $.each(stat_obj, function(sid, stats) {
                    //check if player exists on page already
                    name_element = llWSClient.get_element_cache(sid, sid + ".name");

                    if (name_element) {
                        $.each(stats, function(stat, value) {
                            element_id = sid + "." + stat;
                
                            //console.log("SID: %s, STAT: %s, VALUE: %s, HTML ELEMENT: %s", sid, stat, value, element_id);

                            if (stat === "team") {
                                /* this is a team colour, which we should set the player's name class to */
                                name_class = llWSClient.get_name_class(value);

                                if (name_class !== "no_team_player" && !$(name_element).hasClass(name_class)) {
                                    $(name_element).addClass(name_class);
                                }
                            } else if (stat === "name") {
                                name_element.innerHTML = value;

                                med_element = llWSClient.get_element_cache(sid, sid + ".med_name");

                                if (med_element) {
                                    med_element.innerHTML = value;
                                }

                            } else {
                                element = llWSClient.get_element_cache(sid, element_id);
                                
                                if (element) {
                                    if (stat === "class") {
                                        classes = llWSClient.convert_player_classes(value);
                                        console.log("have class key, class img string: %s", classes);

                                        element.innerHTML = classes;
                                        
                                        /*med_element = llWSClient.get_element_cache(sid, sid + ".med_class");

                                        if (med_element) {
                                            llWSClient.updateTableCell("#medic_stats", med_element, classes);
                                        }*/

                                    } else if (HAD_FIRST_UPDATE) {
                                        if (stat === "healing_done" || stat === "ubers_used" || stat === "ubers_lost" || stat === "overhealing_done") {
                                            llWSClient.updateTableCell("#medic_stats", element, Number(element.innerHTML) + Number(value));
                                        } else {
                                            llWSClient.updateTableCell("#general_stats", element, Number(element.innerHTML) + Number(value));
                                        }
                                    } else {
                                        if (stat === "healing_done" || stat === "ubers_used" || stat === "ubers_lost" || stat === "overhealing_done") {
                                            llWSClient.updateTableCell("#medic_stats", element, Number(value));
                                        } else {
                                            llWSClient.updateTableCell("#general_stats", element, Number(value));
                                        }
                                    }
                                    
                                    //console.log("Element new value: %s", element.innerHTML);
                                }
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
                        //create new row using javascript, populate it with appropriate ids, then add it to the table

                        llWSClient.add_new_stat_row(sid, stats);

                        if ("healing_done" in stats || "ubers_used" in stats || "ubers_lost" in stats || "overhealing_done" in stats) {
                            //player is a medic, need to add medic stat row
                            llWSClient.add_new_medic_row(sid, stats);
                        }
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
                var element, element_id, team_name, special_element_tags = ["team_dpm"], i, tmp, num_rounds, deaths, damage, kills, tmp_result;

                $.each(stat_obj, function(team, team_stat) {
                    team_name = llWSClient.get_element_cache(team, team + ".team");

                    if (team_name) {
                        $.each(team_stat, function(stat, value) {
                            element_id = team + "." + stat;

                            //console.log("Team: %s, stat: %s, value: %s, element_id: %s", team, stat, value, element_id);

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
                                if (tmp === "team_dpm") {
                                    tmp_result = Math.round(damage / (time_elapsed_sec/60 || 1) * 100) / 100;
                                }

                                llWSClient.updateTableCell("#team_stats", element, tmp_result);
                            }
                        }
                    } else {
                        //create new row using javascript, populate it with appropriate ids, then add it to the table
                        if (team !== "None") {
                            llWSClient.add_new_team_row(team, team_stat);
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
            if (typeof sid === 'undefined' || typeof element_id === 'undefined') {
                console.log("ERROR: BAD PARAMETERS PASSED TO get_element_cache");
                return null;
            }

            if (!(sid in client_index)) {
                //add the client sid to the element cache. the sid will contain an array of stats and their page elements
                client_index.sid = [];
            }

            var element = null;

            if (!(element_id in client_index.sid) || (client_index.sid.element_id === null)) {
                element = document.getElementById(element_id);

                if (element === null) {
                    return null;
                }

                client_index.sid.element_id = element; //add the element to the client's element cache
            } else {
                element = client_index.sid.element_id;
            }

            //return the element
            return element;
        },

        add_new_stat_row : function(sid, stats) {
            var column_ids = ["name", "kills", "deaths", "assists", "captures", "headshots", "points", "damage_dealt", "damage_taken",
                    "healing_received", "overhealing_received", "kpd", "dpd", "dpr", "dpm"];

            var row, i, column, tmp, tmp_result, name_class, class_span, name_link;

            row = document.createElement("tr"); //create row
            /* 
            now loop over all column ids, so we have data in the right order
            if a column has no data attached to it, just set it to 0
            */

            column = row.insertCell(0);

            /* construct the name link and class span & append it to the column as children */
            class_span = document.createElement("span"); 
            name_link = document.createElement("a");
            
            class_span.id = sid + ".class";
            class_span.innerHTML = this.convert_player_classes(stats.class);    

            name_link.id = sid + ".name";
            name_link.href = "/player/" + sid;
            name_link.innerHTML = typeof stats.name === 'undefined' ? sid : stats.name;

            $(name_link).addClass("player_community_id_link");

            name_class = this.get_name_class(stats.team);

            $(name_link).addClass(name_class);

            column.appendChild(class_span);
            column.appendChild(name_link);

            /* iterate over the rest of the columns */
            for (i = 1; i < column_ids.length; i++) {
                tmp = column_ids[i];

                if (tmp in stats) {
                    tmp_result = Number(stats[tmp]);
                } else {
                    tmp_result = 0;
                }

                column = row.insertCell(i);
                column.id = sid + "." + tmp;
                column.innerHTML = tmp_result;

                //console.log("new column to be added in new row, id: %s, value: %s", column.id, tmp_result);
            }

            console.log(row);

            this.addTableRow("#general_stats", row);
        },

        add_new_medic_row : function(sid, stats) {
            var column_ids = ["name", "healing_done", "overhealing_done", "ubers_used", "ubers_lost"];

            var row, i, column, tmp, tmp_result, name_class, class_span, name_link;

            row = document.createElement("tr"); //create row
            /* 
            now loop over all column ids, so we have data in the right order
            if a column has no data attached to it, just set it to 0
            */

            column = row.insertCell(0);

            /* construct the name link and class span & append it to the column as children */
            class_span = document.createElement("span");
            name_link = document.createElement("a");
            
            class_span.id = sid + ".med_class";
            class_span.innerHTML = this.convert_player_classes(stats.class);    

            name_link.id = sid + ".med_name";
            name_link.href = "/player/" + sid;
            name_link.innerHTML = sid;

            $(name_link).addClass("player_community_id_link");

            name_class = this.get_name_class(stats.team);

            $(name_link).addClass(name_class);

            column.appendChild(class_span);
            column.appendChild(name_link);

            for (i = 1; i < column_ids.length; i++) {
                tmp = column_ids[i];

                if (tmp in stats) {
                    tmp_result = Number(stats[tmp]);
                }
                else {
                    tmp_result = 0;
                }

                column = row.insertCell(i);
                column.id = sid + "." + tmp;
                column.innerHTML = tmp_result;
            }

            console.log(row);

            this.addTableRow("#medic_stats", row);
        },

        add_new_team_row : function(team, team_stats) {
            var column_ids = ["team_name", "team_kills", "team_deaths", "team_healing_done", "team_overhealing_done", "team_damage_dealt", "team_dpm"];
            
            var row, i, column, tmp, tmp_result;

            row = document.createElement("tr"); //create row

            /* 
            now loop over all column ids, so we have data in the right order
            if a column has no data attached to it, just set it to 0
            */

            //first col is team name
            column = row.insertCell(0);
            column.id = team + ".team";
            column.innerHTML = team.toUpperCase();

            $(column).addClass(this.get_team_class(team));

            for (i = 1; i < column_ids.length; i++) {
                tmp = column_ids[i];

                if (tmp in team_stats) {
                    tmp_result = Number(team_stats[tmp]);
                } else {
                    tmp_result = 0;
                }

                column = row.insertCell(i);
                column.id = team + "." + tmp;
                column.innerHTML = tmp_result;

                //console.log("new column to be added in new row, id: %s, value: %s", column.id, tmp_result);
            }

            console.log(row);

            this.addTableRow("#team_stats", row);
        },

        addTableRow : function(table_id, row_element) {
            var table = $(table_id).dataTable();

            table.fnAddTr(row_element, false);
        },

        convert_player_classes : function(class_string) {
            if (typeof class_string === 'undefined') {
                return '<img src="/images/classes/noclass.png" style="max-width: 18px; max-height: 18px; height: auto; width: auto" alt="noclass"> ';
            }

            var classes = class_string.split(','), rtn_string = " ", pclass;

            for (var i = 0; i < classes.length; i++) {
                pclass = classes[i];

                if (pclass === "UNKNOWN") {
                    pclass = "noclass";
                }

                rtn_string += '<img src="/images/classes/' + pclass + '.png" style="max-width: 18px; max-height: 18px; height: auto; width: auto" alt="' + pclass + '" title="' + pclass + '"> ';
            }

            return rtn_string;
        },

        get_name_class : function(team) {
            /* converts a team to a player CSS class for styling */
            if (typeof team === 'undefined') {
                return "no_team_player";

            } else if (team === "red") {
                return "red_player";

            } else if (team === "blue") {
                return "blue_player";

            } else {
                return "no_team_player";
            }
        },

        get_team_class : function(team) {
            /* converts a team to the team CSS classes for team stats styling */
            if (typeof team === 'undefined') {
                return "no_team_player";

            } else if (team === "red") {
                return "red_score_tag " + this.get_name_class(team);

            } else if (team === "blue") {
                return "blue_score_tag " + this.get_name_class(team);

            } else {
                return;
            }
        }
    };
}());

window.onbeforeunload = function() {
    "use strict";
    if (llWSClient.client) {
        llWSClient.client.close();
    }
};


