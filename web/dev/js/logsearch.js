/* js used to dynamically generate the search results for past logs */

    $(document).ready( function() 
    {
        /*After a user lets go of a key (i.e, they've entered something in the search box,
        we use jquery.get() to call a php script that will return the results (if there are any)
        */
        $('#searchField').keyup( function()
        {
            var search = $(this).val(); //the search term
            
            if (search !== "") //user wasn't clearing the field, but entering something
            {
                //use jquery.get to call logsearch.php with the search term
                $.get("func/logsearch.php?term="+search, function(result)
                {
                    if (result) //result is not empty
                    {
                        $('#pastLogs').html(result); //result will be in the form of standard table rows/columns
                    } else {
                        $('#pastlogs').html('No results available');
                    }
                });
            }
        });
        
    });