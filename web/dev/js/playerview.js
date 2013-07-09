/* Bootstrap style pagination. Author: Allan Jardine @ http://sprymedia.co.uk/

/* API method to get paging information */
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
                    '<li class="prev disabled"><a href="#">&larr; '+oLang.sPrevious+'</a></li>'+
                    '<li class="next disabled"><a href="#">'+oLang.sNext+' &rarr; </a></li>'+
                '</ul>'
            );
            var els = $('a', nPaging);
            $(els[0]).bind( 'click.DT', { action: "previous" }, fnClickHandler );
            $(els[1]).bind( 'click.DT', { action: "next" }, fnClickHandler );
        },
 
        "fnUpdate": function ( oSettings, fnDraw ) {
            var iListLength = 5;
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
 
            for ( i=0, iLen=an.length ; i<iLen ; i++ ) {
                // Remove the middle elements
                $('li:gt(0)', an[i]).filter(':not(:last)').remove();
 
                // Add the new list items and their event handlers
                for ( j=iStart ; j<=iEnd ; j++ ) {
                    sClass = (j==oPaging.iPage+1) ? 'class="active"' : '';
                    $('<li '+sClass+'><a href="#">'+j+'</a></li>')
                        .insertBefore( $('li:last', an[i])[0] )
                        .bind('click', function (e) {
                            e.preventDefault();
                            oSettings._iDisplayStart = (parseInt($('a', this).text(),10)-1) * oPaging.iLength;
                            fnDraw( oSettings );
                        } );
                }
 
                // Add / remove disabled classes from the static elements
                if ( oPaging.iPage === 0 ) {
                    $('li:first', an[i]).addClass('disabled');
                } else {
                    $('li:first', an[i]).removeClass('disabled');
                }
 
                if ( oPaging.iPage === oPaging.iTotalPages-1 || oPaging.iTotalPages === 0 ) {
                    $('li:last', an[i]).addClass('disabled');
                } else {
                    $('li:last', an[i]).removeClass('disabled');
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
    return {
        init : function(community_id, num_preloaded, total_logs) {
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
                //"fnServerData": ll_paging.datatables_pipeline,
                "fnServerParams": function (aoData) {
                    aoData.push({ "cid": community_id });
                }
            });
        },

        datatables_pipeline : function (source, data, callback)
        {
            var pipe_len = 4; /* how many pages to preload */


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

