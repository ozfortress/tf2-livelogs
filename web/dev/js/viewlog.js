/* js used to modify tables and what not inside the log view page
 * will probably also contain stuff for real-time display
 */
 
$(document).ready(function()
{
    "use strict";
    $('#general_stats').dataTable( {
        "aaSorting": [[1, 'desc']],
        "aoColumnDefs": [
            { "sType": "html", "bSearchable": false, "aTargets": [0] },
            { "sType": "dt-numeric-html", "bSearchable": false, "aTargets": ["_all"] }
        ],
        "bPaginate": false,
        "bAutoWidth": false,
        "bSortClasses": false,
        "bSearchable": false,
        "bInfo": false,
        "bJQueryUI": true,
        "bUseRendered": true,
        "bFilter": false
    } );
} );

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
    var client = null, ws = null, connect_msg = {}, HAD_FIRST_UPDATE = false, auto_update = true; //our client socket and message that will be sent on connect, containing the log id

    return {
        init : function(ip, port, log_id) {
            ws = "ws://" + ip + ":" + port + "/logupdate";
            
            console.log("WS URI: %s", ws);
            
            connect_msg.ident = log_id;
            
            this.clientConnect(ws);
        },
        
        clientConnect : function(ws_uri) {
            try {
                if (!window.WebSocket) {
                    if (window.MozWebSocket) {
                        client = new MozWebSocket(ws_uri);
                        client.onmessage = function(msg) { llWSClient.onMessage(msg); };
                        client.onopen = function(event) { llWSClient.onOpen(event); };
                        client.onclose = function(event) { llWSClient.onClose(event); };
                        client.onerror = function(event) { llWSClient.onError(event); };
                    } else {
                        console.log("Websockets not supported");
                        return;
                    }
                } else {
                    client = new WebSocket(ws_uri);
                    client.onmessage = function(msg) { llWSClient.onMessage(msg); };
                    client.onopen = function(event) { llWSClient.onOpen(event); };
                    client.onclose = function(event) { llWSClient.onClose(event); };
                    client.onerror = function(event) { llWSClient.onError(event); };
                }
            }
            catch (error) {
                console.log("Had error trying to establish websocket: %s", error);
                return;
            }
        },
        
        onOpen : function(event) {
            console.log("Client websock opened");
            client.send(JSON.stringify(connect_msg));
        },
        
        onClose : function(event) {
            console.log("Client websocket closed: %s", event);
        },
        
        onError : function(event) {
            console.log("Had WS error: " + event);
        },
        
        onMessage : function(msg) {
            var msg_data = msg.data, update_json, element;
            console.log("MESSAGE: " + msg_data);
            
            if (msg_data === "LOG_NOT_LIVE") {
                console.log("Log not live. Closing connection");
                //the server may have closed the connection before us, so it needs to be checked
                if (client) {
                    client.close(400);
                }
                
                client = null;
            } else if (!auto_update) {
                return;
                
            } else if (msg_data === "LOG_IS_LIVE") {
                HAD_FIRST_UPDATE = false;

            } else if (msg_data == "LOG_END") {
                this.client.close(200);
                //update status element with "Complete"

                element = document.getElementById("#log_status_span");

                if ($("#log_status_span").hasClass("text-success")) { //if it has the text-success class, remove it and add text-error (red)
                    $("#log_status_span").removeClass("text-success");

                    $("#log_status_span").addClass("text-error");
                }

                element.innerHTML = "Complete"; 

            } else {
                //all other messages are json encoded packets
                if (!HAD_FIRST_UPDATE) {
                    //the first message sent is a full update, so the client and server are in sync
                    try {
                        update_json = jQuery.parseJSON(msg_data);
                    }
                    catch (exception) {
                        console.log("Error trying to decode or parse json. Message: %s, ERROR: %s", msg_data, exception);
                        return;
                    }
                    
                    this.parseStatUpdate(update_json);
                        
                    HAD_FIRST_UPDATE = true;
                    
                } else {
                    try {
                        update_json = jQuery.parseJSON(msg_data);
                    }
                    catch (exception) {
                        console.log("Error trying to decode or parse json. Message: %s, ERROR: %s", msg_data, exception);
                        return;
                    }
                    
                    //there's multiple other possible json packets we can receive. Need to go through them, before defaulting to a stat update

                    //first structure: [{"time": "unix timestamp"}]
                    //second structure: [{"score": {{"red": val}, {"blue": val}}}]
                    //third structure: [{"chat": {{"name": {{"message": msg}, {"msg_type": team/all}, {"team": team colour}}}, repeat}}]
                    //and finally, a stat object: [{"sid": {{"type": val}, ...}, {"sid": .....}, repeat]

                    if (update_json["time"] != undefined) {
                        //update the time. requires use of sprintf
                        var timestamp = Number(update_json["time"]); //make sure the timestamp is a number

                        console.log("Got timestamp message. Timestamp: %d", timestamp);

                        element = document.getElementById("#time_elapsed");
                        element.innerHTML = sprintf("%02d minute(s) and %02d second(s)", (timestamp/60)%60, timestamp%60);

                    } else if (update_json["score"] != undefined) {
                        var red_score, blue_score;

                        red_score = Number(update_json.score.red);
                        blue_score = Number(update_json.score.blue);

                        console.log("SCORE UPDATE. RED: %d BLUE: %d", red_score, blue_score);

                        document.getElementById("#red_score_value").innerHTML = red_score;
                        document.getElementById("#blue_score_value").innerHTML = blue_score;

                    } else if (update_json["chat"] != undefined) {
                        var chat_name, chat_team, chat_type, chat_message;
                        //underneath "chat" is the player names and the message
                        $.each(update_json.chat, function(player_name, data) {
                            //data will be all the message shit

                        });

                        $("table#chat_table tbody").append('
                            <tr>
                                <td><span class=""');



                    } else {
                        //default update type
                        this.parseStatUpdate(update_json);
                    }
                }
            }
        },
        
        parseStatUpdate : function(stat_obj) {
            try {
                var element, element_id, special_element_tags = ["kpd", "dpd", "dpr"], i, tmp, num_rounds, deaths, damage, kills;
                num_rounds = Number(document.getElementById("red_score_value").innerHTML) + Number(document.getElementById("blue_score_value").innerHTML);
                
                $.each(stat_obj, function(sid, stats) {
                    $.each(stats, function(stat, value) {
                        element_id = sid + "." + stat;
                        
                        console.log("SID: %s, STAT: %s, VALUE: %s, HTML ELEMENT: %s", sid, stat, value, element_id);
                        
                        element = document.getElementById(element_id);
                        if (element) {
                            console.log("Got element %s, VALUE: %s", element, element.innerHTML);
                            
                            if (HAD_FIRST_UPDATE) {                    
                                element.innerHTML = Number(element.innerHTML) + Number(value);
                            } else {
                                element.innerHTML = Number(value);
                            }
                            
                            console.log("Element new value: %s", element.innerHTML);
                        }
                    });
                    
                    /*now that we've looped through all the stats, we need to edit the combo columns like kpd, dpd and dpr*/
                    for (i = 0; i < special_element_tags.length; i++) {
                        tmp = special_element_tags[i];
                        element_id = sid + "." + tmp;
                        element = document.getElementById(element_id);
                        
                        console.log("SID: %s, HTML ELEMENT: %s", sid, element_id);
                        
                        
                        deaths = Number(document.getElementById(sid + ".deaths").innerHTML);
                        damage = Number(document.getElementById(sid + ".damage").innerHTML);
                        
                        if (element) {
                            if (tmp === "kpd") {
                                kills = Number(document.getElementById(sid + ".kills").innerHTML);
                                element.innerHTML = Math.round(kills / (deaths || 1) * 100) / 100; //multiply by 100 and div by 100 for 2 dec places rounding
                            } else if (tmp === "dpd") {
                                element.innerHTML = Math.round(damage / (deaths || 1) * 100) / 100;
                            } else if (tmp === "dpr") {
                                element.innerHTML = Math.round(damage / (num_rounds || 1) * 100) / 100;
                            } else {
                                console.log("Invalid element %s in special element array", tmp);
                            }
                        }
                    }
                });
            }
            catch (exception) {
                console.log("Exception trying to parse stat update. Error: %s", exception);
            }
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
        }
    };
}());

window.onbeforeunload = function() {
    if (llWSClient.client) {
        llWSClient.client.close();
    }
};
    