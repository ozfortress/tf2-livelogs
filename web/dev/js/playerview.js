$(document).ready(function()
{
    "use strict";
    var stat_table = $('#class_stats').dataTable( {
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
        "bJQueryUI": true,
        "bUseRendered": true,
        "bFilter": false
    });
});