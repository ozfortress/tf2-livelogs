/* js used to modify tables and what not inside the log view page
 * will probably also contain stuff for real-time display
 */
 
    $(document).ready( function() 
    {
        $('#general_stats').dataTable( {
            "aaSorting": [[2, 'asc']],
            "bPaginate": false,
            "bAutoWidth": false,
            "bSortClasses": false,
            "bSearchable": true,
            "bInfo": false,
            "bJQueryUI": true,
            
        } );
    } );
