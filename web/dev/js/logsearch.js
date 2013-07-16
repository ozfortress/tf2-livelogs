/* Uses ajax to get search results using a php script */

var log_search = log_search || (function() {
    "use strict";
    var search, past_search, state_obj = {}, search_field = null;

    var pipe_cache = {
            cache_start: -1,
            cache_end: -1,
            last_request: null
        };

    var initialised = false;
    return {
        init : function(default_search, display_length) {
            console.log("search: %s | display_length: %s", default_search, display_length);
            if (initialised) { return; }

            var past_table = $('#past_logs').dataTable( {
                "aaSorting": [[4, 'desc']],
                "aoColumnDefs": [
                    { "sType": "ip-address", "bSearchable": false, "aTargets": [0] },
                    { "sType": "numeric", "aTargets": [1]},
                    { "sType": "iso8601-datetime", "bSearchable": false, "aTargets": [4]},
                    { "sType": "string", "bSearchable": false, "aTargets": ["_all"] }, //rest are just string
                    { "asSorting": [ "desc", "asc" ], "aTargets": [ "_all" ] } //default desc -> asc sorting
                ],
                "bAutoWidth": false,
                "bSortClasses": false,
                "bSearchable": true,
                "oSearch": { "sSearch": default_search },
                "bInfo": false,
                "bJQueryUI": false,
                "bUseRendered": true,
                "bFilter": true,
                "bPaginate": true,
                "sPaginationType": "bootstrap",
                "bLengthChange": false,
                "iDisplayLength": display_length,
                "bProcessing": true,
                "bServerSide": true,
                "sAjaxSource": "/func/logsearch.php",
                "fnServerData": log_search.datatables_pipeline
            });

            initialised = true;
        },

        datatables_getkey : function(data, key) {
            for (var i = 0, dlen = data.length; i < dlen; i++) {
                if (data[i].name === key) {
                    return data[i].value;
                }
            }

            return null;
        },

        datatables_setkey : function(data, key, value) {
            for (var i = 0, dlen = data.length; i < dlen; i++) {
                if (data[i].name === key) {
                    data[i].value = value;
                }
            }
        },

        datatables_pipeline : function(data_source, request_data, datatables_callback) {
            console.log(request_data);

            var pipe_len = 8, /* how many pages to preload */
            need_server = false, 
            challenge_echo = log_search.datatables_getkey(request_data, "sEcho"),
            request_start = log_search.datatables_getkey(request_data, "iDisplayStart"),
            display_length = log_search.datatables_getkey(request_data, "iDisplayLength"),
            request_end = request_start + display_length;

            pipe_cache.display_start = request_start;

            /* check if the requested data is outside the cache or not */
            if (pipe_cache.cache_start < 0 || request_start < pipe_cache.cache_start || request_end > pipe_cache.cache_end) {
                //data is outside the cache, so we need to get more data from the server
                need_server = true;
            }

            /* check if the sorting has changed */
            if (pipe_cache.last_request && !need_server) {
                for (var i = 0, dlen = request_data.length; i < dlen; i++) {
                    if (request_data[i].name !== "iDisplayStart" && request_data[i].name !== "iDisplayLength" && request_data[i].name !== "sEcho") {
                        if (request_data[i].value !== pipe_cache.last_request[i].value) {
                            need_server = true; //data is different from what is cached, we need to re-cache
                            break;
                        }
                    }
                }
            }

            //store the request for the next check
            pipe_cache.last_request = request_data.slice();

            if (need_server) {
                /* let's get some data from daaa server */

                //if the requested starting position is below the the cache's lowest position, we want to go down a page
                if (request_start < pipe_cache.cache_start) {
                    request_start = request_start - display_length * (pipe_len - 1);

                    if (request_start < 0) {
                        request_start = 0;
                    }
                }

                pipe_cache.cache_start = request_start;
                pipe_cache.cache_end = request_start + (display_length * pipe_len);
                pipe_cache.display_length = display_length;

                //set the request_data's lengths to the lengths of the pipeline
                log_search.datatables_setkey(request_data, "iDisplayStart", request_start);
                log_search.datatables_setkey(request_data, "iDisplayLength", display_length * pipe_len);

                $.getJSON(data_source, request_data, function(json) {
                    pipe_cache.last_json = jQuery.extend(true, {}, json);

                    if (pipe_cache.cache_start !== pipe_cache.display_start) {
                        //if the cache start != the display start, we have to splice from 0 up to the cache starting position first
                        json.aaData.splice(0, pipe_cache.display_start - pipe_cache.cache_start);
                    }

                    json.aaData.splice(pipe_cache.display_length, json.aaData.length); //split the return data in a segment of display_length for returning

                    datatables_callback(json);
                });    
            }
            else {
                //dont need to request data from the server
                var json = jQuery.extend(true, {}, pipe_cache.last_json); //get our json out from the last server request

                json.sEcho = challenge_echo;
                json.aaData.splice(0, request_start - pipe_cache.cache_start);
                json.aaData.splice(display_length, json.aaData.length);

                datatables_callback(json);
            }
        },

        searchLogs : function() {
            if (search_field === null) {
                search_field = $("#search_field");
            }

            search = search_field.val();

            if (search === past_search) {
                return;
            }
            else {
                past_search = search;
            }

            if (search !== "") {
                
            }
        },

        submitCallback : function() {
            log_search.searchLogs();
        },

        keyupCallback : function(e) {
            if (e.keyCode !== 13) {
                log_search.searchLogs();
            }
        },

        set_search_url : function(search) {
            state_obj.search = search;
            history.pushState(state_obj, "Search result for " + search, "/past/" + search.replace(" ", "%20"));
        }
    };
}());

$(document).ready(function() 
{
    "use strict";
    /*
    After a user lets go of a key (i.e, they've entered something in the search box,
    we use jquery.get() to call a php script that will return the results (if there are any)
    */
    
    //$("#search_field").bindWithDelay("keyup", {when: "delay", optional: "eventData"}, log_search.keyupCallback, 300);

    $("#search_form").submit(function(e) {
        log_search.submitCallback();
        e.preventDefault();
    });
});