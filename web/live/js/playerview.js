/* init data tables */
$(document).ready(function() {
    "use strict";
    var stat_table = $('#class_stats').dataTable( {
        "aaSorting": [[1, 'desc']],
        "aoColumnDefs": [
            { "sType": "alt-string", "bSearchable": false, "aTargets": [0] },
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

var ll_paging = ll_paging || (function() {
    "use strict";

    var pipe_cache = {
            cache_start: -1,
            cache_end: -1,
            last_request: null
        };

    var initialised = false;

    return {
        init : function(community_id, display_length) {
            console.log("cid: %s | display_length: %s", community_id, display_length);
            if (initialised) return;

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
                "bSearchable": false,
                "bInfo": false,
                "bJQueryUI": false,
                "bUseRendered": true,
                "bFilter": false,
                "bPaginate": true,
                "sPaginationType": "bootstrap",
                "bLengthChange": false,
                "iDisplayLength": display_length,
                "bProcessing": true,
                "bServerSide": true,
                "sAjaxSource": "/func/paging_data.php",
                "fnServerData": ll_paging.datatables_pipeline,
                "fnServerParams": function (aoData) {
                    aoData.push({ "name": "cid", "value": community_id });
                }
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
            var pipe_len = 8, /* how many pages to preload */
            need_server = false, 
            challenge_echo = ll_paging.datatables_getkey(request_data, "sEcho"),
            request_start = ll_paging.datatables_getkey(request_data, "iDisplayStart"),
            display_length = ll_paging.datatables_getkey(request_data, "iDisplayLength"),
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
                ll_paging.datatables_setkey(request_data, "iDisplayStart", request_start);
                ll_paging.datatables_setkey(request_data, "iDisplayLength", display_length * pipe_len);

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
        }
    }
}());

