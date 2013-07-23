/* 
    Bootstrap style pagination. Author: Allan Jardine @ http://sprymedia.co.uk/

    Modifed to have first & last controls
 */

//API method to get paging information 
$.fn.dataTableExt.oApi.fnPagingInfo = function ( oSettings ) {
    "use strict";
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
};
 
/* Bootstrap style pagination control */
$.extend( $.fn.dataTableExt.oPagination, {
    "bootstrap": {
        "fnInit": function( oSettings, nPaging, fnDraw ) {
            "use strict";
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
            "use strict";
            var iListLength = 8;
            var oPaging = oSettings.oInstance.fnPagingInfo();
            var an = oSettings.aanFeatures.p;
            var i, j, iLen, sClass, iStart, iEnd, iHalf=Math.floor(iListLength/2);
 
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
            for (i = 0, iLen=an.length ; i<iLen ; i++ ) {
                // Remove the middle elements
                paging_ul = $(an[i]).children().children();
                $(paging_ul).slice(2, paging_ul.length-2).remove(); //remove elements between the controls
 
                // Add the new list items and their event handlers
                for ( j=iStart ; j<=iEnd ; j++ ) {
                    sClass = (j === oPaging.iPage+1) ? 'class="active"' : '';
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

jQuery.extend( jQuery.fn.dataTableExt.oSort, {
    /*IP SORTING CREDIT TO Brad Wasson */
    "ip-address-pre": function ( a ) {
        var m = a.split("."), x = "";
 
        for (var i = 0; i < m.length; i++) {
            var item = m[i];
            if (item.length === 1) {
                x += "00" + item;
            } else if (item.length === 2) {
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
        for (var i=date_a.length; i--;) { 
            date_a[i] = parseInt(date_a[i], 10); 
        }

        for (i=time_a.length; i--;) { 
            time_a[i] = parseInt(time_a[i], 10); 
        }

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

/* api function for adding row elements to datatables while maintaining custom classes/ids */
$.fn.dataTableExt.oApi.fnAddTr = function ( oSettings, nTr, bRedraw ) {
    if ( typeof bRedraw == 'undefined' )
    {
        bRedraw = true;
    }
      
    var nTds = nTr.getElementsByTagName('td');
    if ( nTds.length != oSettings.aoColumns.length )
    {
        alert( 'Warning: not adding new TR - columns and TD elements must match' );
        return;
    }
      
    var aData = [];
    for ( var i=0 ; i<nTds.length ; i++ )
    {
        aData.push( nTds[i].innerHTML );
    }
      
    /* Add the data and then replace DataTable's generated TR with ours */
    var iIndex = this.oApi._fnAddData( oSettings, aData );
    nTr._DT_RowIndex = iIndex;
    oSettings.aoData[ iIndex ].nTr = nTr;
      
    oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();
      
    if ( bRedraw )
    {
        this.oApi._fnReDraw( oSettings );
    }
};

