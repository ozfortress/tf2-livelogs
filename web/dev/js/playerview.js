/* 
    Bootstrap style pagination. Author: Allan Jardine @ http://sprymedia.co.uk/

    Modifed to have first & last controls
 */

//API method to get paging information 
$.fn.dataTableExt.oApi.fnPagingInfo = function ( oSettings )
{
    return {
        "iStart":         oSettings._iDisplayStart,
        "iEnd":           oSettings.fnDisplayEnd(),
        "iLength":        oSettings._iDisplayLength,
        "iTotal":         oSettings.fnRecordsTotal(),
        "iFilteredTotal": oSettings.fnRecordsDisplay(),
        "iPage":          oSettings._iDisplayLength === -1 ?
            0 : Math.ceil( oSettings._iDisplayStart / oSettings._iDisplayLength ),
        "iTotalPages":    oSettings._iDisplayLength === -1 ?
            0 : Math.ceil( oSettings.fnRecordsDisplay() / oSettings._iDisplayLength )
    };
}
 
/* Bootstrap style pagination control */
$.extend( $.fn.dataTableExt.oPagination, {
    "bootstrap": {
        "fnInit": function( oSettings, nPaging, fnDraw ) {
            var oLang = oSettings.oLanguage.oPaginate;
            var fnClickHandler = function ( e ) {
                e.preventDefault();
                if ( oSettings.oApi._fnPageChange(oSettings, e.data.action) ) {
                    fnDraw( oSettings );
                }
            };
 
            $(nPaging).addClass('pagination').append(
                '<ul>'+
                    '<li class="first disabled"><a href="#">&larr; '+oLang.sFirst+'</a></li>'+
                    '<li class="prev disabled"><a href="#">'+oLang.sPrevious+'</a></li>'+
                    '<li class="next disabled"><a href="#">'+oLang.sNext+'</a></li>'+
                    '<li class="last disabled"><a href="#">'+oLang.sLast+' &rarr;</a></li>'+
                '</ul>'
            );
            var els = $('a', nPaging);
            $(els[0]).bind( 'click.DT', { action: "first" }, fnClickHandler );
            $(els[1]).bind( 'click.DT', { action: "previous" }, fnClickHandler );
            $(els[2]).bind( 'click.DT', { action: "next" }, fnClickHandler );
            $(els[3]).bind( 'click.DT', { action: "last" }, fnClickHandler );
        },
 
        "fnUpdate": function ( oSettings, fnDraw ) {
            var iListLength = 8;
            var oPaging = oSettings.oInstance.fnPagingInfo();
            var an = oSettings.aanFeatures.p;
            var i, j, sClass, iStart, iEnd, iHalf=Math.floor(iListLength/2);
 
            if ( oPaging.iTotalPages < iListLength) {
                iStart = 1;
                iEnd = oPaging.iTotalPages;
            }
            else if ( oPaging.iPage <= iHalf ) {
                iStart = 1;
                iEnd = iListLength;
            } else if ( oPaging.iPage >= (oPaging.iTotalPages-iHalf) ) {
                iStart = oPaging.iTotalPages - iListLength + 1;
                iEnd = oPaging.iTotalPages;
            } else {
                iStart = oPaging.iPage - iHalf + 1;
                iEnd = iStart + iListLength - 1;
            }
 
            var paging_ul = null;
            for ( i=0, iLen=an.length ; i<iLen ; i++ ) {
                // Remove the middle elements
                paging_ul = $(an[i]).children().children();
                $(paging_ul).slice(2, paging_ul.length-2).remove(); //remove elements between the controls
 
                // Add the new list items and their event handlers
                for ( j=iStart ; j<=iEnd ; j++ ) {
                    sClass = (j==oPaging.iPage+1) ? 'class="active"' : '';
                    $('<li '+sClass+'><a href="#">'+j+'</a></li>')
                        .insertBefore( $('li:nth-last-child(2)', an[i])[0] ) //insert before the 2nd last element
                        .bind('click', function (e) {
                            e.preventDefault();
                            oSettings._iDisplayStart = (parseInt($('a', this).text(),10)-1) * oPaging.iLength;
                            fnDraw( oSettings );
                        } );
                }
 
                // Add / remove disabled classes from the static elements
                if ( oPaging.iPage === 0 ) {
                    $('li:first', an[i]).addClass('disabled');
                    $('li:nth-child(2)', an[i]).addClass('disabled');
                } else {
                    $('li:first', an[i]).removeClass('disabled');
                    $('li:nth-child(2)', an[i]).removeClass('disabled');
                }
 
                if ( oPaging.iPage === oPaging.iTotalPages-1 || oPaging.iTotalPages === 0 ) {
                    $('li:last', an[i]).addClass('disabled');
                    $('li:nth-last-child(2)', an[i]).addClass('disabled');
                } else {
                    $('li:last', an[i]).removeClass('disabled');
                    $('li:nth-last-child(2)', an[i]).removeClass('disabled');
                }
            }
        }
    }
} );

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
    var pipe_cache = {
            cache_start: -1,
            cache_end: -1,
            last_request: null
        };

    return {
        init : function(community_id, num_preloaded, total_logs) {
            console.log("cid: %s | num_preloaded: %s | total: %s", community_id, num_preloaded, total_logs);
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
                "iDisplayLength": num_preloaded,
                "bProcessing": true,
                "bServerSide": true,
                "sAjaxSource": "/func/paging_data.php",
                "iDeferLoading": total_logs,
                "fnServerData": ll_paging.datatables_pipeline,
                "fnServerParams": function (aoData) {
                    aoData.push({ "name": "cid", "value": community_id });
                }
            });
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
                        if (request_data[i].value != pipe_cache.last_request[i].value) {
                            need_server = true //data is different from what is cached, we need to re-cache
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

                    if (pipe_cache.cache_start != pipe_cache.display_start) {
                        //if the cache start != the display start, we have to splice from 0 up to the cache starting position first
                        json.aaData.splice(0, pipe_cache.display_start - pipe_cache.cache_start);
                    }

                    json.aaData.splice(pipe_cache.display_length, json.aaData.length); //split the return data in a segment of display_length for returning

                    datatables_callback(json);
                });    
            }
            else {
                //dont need to request data from the server
                json = jQuery.extend(true, {}, pipe_cache.last_json); //get our json out from the last server request

                json.sEcho = challenge_echo;
                json.aaData.splice(0, request_start - pipe_cache.cache_start);
                json.aaData.splice(display_length, json.aaData.length);

                datatables_callback(json);
            }

        },

    }
}());

jQuery.extend( jQuery.fn.dataTableExt.oSort, {
    /*IP SORTING CREDIT TO Brad Wasson */
    "ip-address-pre": function ( a ) {
        var m = a.split("."), x = "";
 
        for(var i = 0; i < m.length; i++) {
            var item = m[i];
            if(item.length == 1) {
                x += "00" + item;
            } else if(item.length == 2) {
                x += "0" + item;
            } else {
                x += item;
            }
        }
 
        return x;
    },
 
    "ip-address-asc": function ( a, b ) {
        return ((a < b) ? -1 : ((a > b) ? 1 : 0));
    },
 
    "ip-address-desc": function ( a, b ) {
        return ((a < b) ? 1 : ((a > b) ? -1 : 0));
    },

    "alt-string-pre": function ( a ) {
        return a.match(/alt="(.*?)"/)[1].toLowerCase();
    },
     
    "alt-string-asc": function( a, b ) {
        return ((a < b) ? -1 : ((a > b) ? 1 : 0));
    },
 
    "alt-string-desc": function(a,b) {
        return ((a < b) ? 1 : ((a > b) ? -1 : 0));
    },

    "iso8601-datetime-pre": function(y) {
        "use strict";
        var a = y.split(' '); //split into [ "2013-07-05", "22:52:42" ]
        var date_a = a[0].split('-'), time_a = a[1].split(':');

        /* convert the string arrays to numbers */
        for (var i=date_a.length; i--;) { date_a[i] = parseInt(date_a[i], 10); };
        for (var i=time_a.length; i--;) { time_a[i] = parseInt(time_a[i], 10); };

        /* convert our date and time to single numbers */
        var x = (date_a[0]*10000 + date_a[1]*100 + date_a[2] + time_a[0]*10000 + time_a[1]*100 + time_a[2]);
        
        console.log("y: %s | date_split: %s | time_split: %s | return: %d", y, date_a, time_a, x);
        return x;
    },

    "iso8601-datetime-asc": function(a, b) {
        "use strict";
        /* 
        the purpose of these sort functions is to return a 1 if a should be moved up,
        -1 if a should be moved down, or 0 if a should remain where it is according to
        whether we want ascending or descending ordering

        this is asc, so if a > b, we want a to be moved up, if a < b, a should be moved down
        */

        console.log("asc logic: %d", ((a > b) ? 1 : ((a < b) ? -1 : 0)));
        return ((a > b) ? 1 : ((a < b) ? -1 : 0));

    },

    "iso8601-datetime-desc": function(a, b) {
        "use strict";
        /* 
        desc, so if a > b, a should be moved down
        */
        
        //if a and b are equal, return 0. if a is > b, return -1 meaning a moves down, 1 when a < b
        //x represents a, y represents b
        
        console.log("desc logic: %d", ((a > b) ? -1 : ((a < b) ? 1 : 0)));
        return ((a > b) ? -1 : ((a < b) ? 1 : 0));
    }
});

