/* Uses ajax to get search results using a php script */

$(document).ready(function() 
{
    /*
    After a user lets go of a key (i.e, they've entered something in the search box,
    we use jquery.get() to call a php script that will return the results (if there are any)
    */
    
    $('#searchField').bindWithDelay(
            "keyup", 
            function(event) {
                var search = $event.val()

                if (search !== "") {
                    $.get("/func/logsearch.php?term=" + search, function(result) {
                        if (result) {
                            $('#pastLogs').html(result); //result is in form of <tr><td></td>...</tr>
                        }
                        else {
                            $('#pastLogs').html("No results available");
                        }
                    });
                }
            },
            1000
        );



    /*
    $('#searchField').keyup(function()
    {
        var search = $(this).val(); //the search term
        
        if (search !== "") //user wasn't clearing the field, but entering something
        {
            //use jquery.get to call logsearch.php with the search term
            $.get("/func/logsearch.php?term=" + search, function(result)
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
    */
    
});