/* js used to modify tables and what not inside the log view page
 * will probably also contain stuff for real-time display
 */
 
    $(document).ready( function()
    {
        $('#general_stats').dataTable( {
            "aaSorting": [[2, 'asc']],
            "aoColumnDefs": [
                { "sType": "html", "bSearchable": true, "aTargets": [0] },
                { "sType": "dt-numeric-html", "bSearchable": false, "aTargets": ["_all"] },
            ],
            "bPaginate": false,
            "bAutoWidth": false,
            "bSortClasses": false,
//            "bSearchable": false,
            "bInfo": false,
            "bJQueryUI": true,
            "bUseRendered": true,
        } );
    } );
    
    jQuery.fn.dataTableExt.oSort['dt-numeric-html-asc'] = function(a,b) {
        var x = a.replace( /<.*?>/g, "" );
        var y = b.replace( /<.*?>/g, "" );
        x = parseFloat( x );
        y = parseFloat( y );
        return ((x < y) ? -1 : ((x > y) ? 1 : 0));
    };

    jQuery.fn.dataTableExt.oSort['dt-numeric-html-desc'] = function(a,b) {
        var x = a.replace( /<.*?>/g, "" );
        var y = b.replace( /<.*?>/g, "" );
        x = parseFloat( x );
        y = parseFloat( y );
        return ((x < y) ? 1 : ((x > y) ? -1 : 0));
    };
