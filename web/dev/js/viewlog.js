/* js used to modify tables and what not inside the log view page
 * will probably also contain stuff for real-time display
 */
 
$(document).ready(function()
{
    "use strict";
    $('#general_stats').dataTable( {
        "aaSorting": [[1, 'dt-numeric-html-asc']],
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
    var client = null, connect_msg = {}, HAD_FIRST_UPDATE = false; //our client socket and message that will be sent on connect, containing the log id

    return {
        init : function(ip, port, log_id) {
            var ws = "ws://" + ip + ":" + port + "/logupdate";
            
            console.log("WS URI: " + ws);
            
            connect_msg.ident = log_id;
            
            try {
                if (!window.WebSocket) {
                    if (window.MozWebSocket) {
                        client = new MozWebSocket(ws);
                        client.onmessage = function(msg) { llWSClient.onMessage(msg); };
                        client.onopen = function(event) { llWSClient.onOpen(event); };
                        client.onclose = function(event) { llWSClient.onClose(event); };
                        client.onerror = function(event) { llWSClient.onError(event); };
                    } else {
                        console.log("Websockets not supported");
                        return;
                    }
                } else {
                    client = new WebSocket(ws);
                    client.onmessage = function(msg) { llWSClient.onMessage(msg); };
                    client.onopen = function(event) { llWSClient.onOpen(event); };
                    client.onclose = function(event) { llWSClient.onClose(event); };
                    client.onerror = function(event) { llWSClient.onError(event); };
                }
            }
            catch (error) {
                console.log("Had error trying to establish websocket: " + error);
                return;
            }
            
        },
        
        onOpen : function(event) {
            console.log("Client websock opened");
            client.send(JSON.stringify(connect_msg));
        },
        
        onClose : function(event) {
            console.log("Client websocket closed");
        },
        
        onError : function(event) {
            console.log("Had WS error: " + event.data);
        },
        
        onMessage : function(msg) {
            var msg_data = msg.data, full_update = null, delta_update = null;
            console.log("MESSAGE: " + msg_data);
            
            if (msg_data === "LOG_NOT_LIVE") {
                console.log("Log not live. Closing connection");
                client.close(400);
                
                client = null;
            } else if (msg_data === "LOG_IS_LIVE") {
                HAD_FIRST_UPDATE = false;
                
            } else {
                //all other messages are json encoded packets
                if (!HAD_FIRST_UPDATE) {
                    //the first message sent is a full update, so the client and server are in sync
                    try {
                        full_update = jQuery.parseJSON(msg_data);
                    }
                    catch (exception) {
                        console.log("Error trying to decode or parse json. Message: %s, ERROR: %s", msg_data, exception);
                        return;
                    }
                    
                    this.parseStatUpdate(full_update);
                        
                    HAD_FIRST_UPDATE = true;
                    
                } else {
                    try {
                        delta_update = jQuery.parseJSON(msg_data);
                    }
                    catch (exception) {
                        console.log("Error trying to decode or parse json. Message: %s, ERROR: %s", msg_data, exception);
                        return;
                    }
                    
                    this.parseStatUpdate(delta_update);
                }
            }
        },
        
        parseStatUpdate : function(stat_obj) {
            try {
                $.each(stat_obj, function(sid, stats) {
                    $.each(stats, function(stat, value) {
                        var element_id = sid + "." + stat;
                        
                        console.log("SID: %s, STAT: %s, VALUE: %s, HTML ELEMENT: %s", sid, stat, value, element_id);
                        
                        var element = document.getElementById(element_id);
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
                
                });
            }
            catch (exception) {
                console.log("Exception trying to parse stat update. Error: %s", exception);
            }
        }
    };
}());
    