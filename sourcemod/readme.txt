livelogs server plugin README updated 26/2/2013

Installation steps:

    - Copy the socket extension for your OS into /tf/addons/sourcemod/extensions (.so for linux, .dll for windows)
    - Copy websocket.smx and livelogs.smx (in the plugins directory) into your sourcemod plugins directory (/tf/addons/sourcemod/plugins)
        * NOTE: If you do not wish to use SourceTV2D, you can simply ignore websocket.smx or use the ConVar supplied to disable it (see below).

    - Restart your server, or load the extension and plugins manually (sm exts load/sm plugins load). A generic config file will be created in your cfg folder called livelogs.cfg
    - Edit the convars in the config file. There are some you must manually add. These include:
        * livelogs_address - The address of the livelogs daemon
        * livelogs_port - The port of the livelogs daemon
        * livelogs_api_key - Your personalised key for authenticating with the daemon (valid only for a single IP address)

        You must contact me (bladez) to obtain the settings for the aforementioned cvars.

    - Further information about convar settings is available below.



livelogs_additional_logging - This is a bitmask of logging options that the plugin should output. It uses the sum of bit values to set a logging level. The bit values are:
    1: damage taken
    2: damage dealt
    4: healing done
    8: item pickups

    So, to enable ALL outputs, the convar should be set to "15" (1 + 2 + 4 + 8). To enable just damage taken, the convar should be set to "1". To disable, set it to "0".

    This is provided so that users may run other plugins that cause additional data to be logged (such as supstats, which outputs damage dealt, item pick ups and healing).

    This convar simply toggles what data is output by the PLUGIN. The daemon will still record any stats output in the same format by other plugins.


livelogs_enable_webtv - Enable/disable SourceTV2D. Setting this to 0 is the equivalent of not having websocket.smx in the plugin directory.


livelogs_webtv_port - What port the SourceTV2D server should listen on. Default is server port + 2. This ConVar is irrelevant if SourceTV2D is disabled.


livelogs_new_log_file - Enable/disable the initialisation of logging on match start using 'log on'. 'log on' is required so that logs are output to the server's console, and hence sent to livelogs.
    If you are running another plugin that enables logging using 'log on' at some point, this can be disabled if you wish. However, you can still leave it on so that fresh log files are created
    in your server's log directory for new matches, if you choose to.

    Setting this convar to "1" will use 'log on'. S

    
livelogs_name - The name that is displayed on the livelogs webpage for logs from your server.


livelogs_tournament_ready_only - Whether to start logging on tournament readies only or not. 
    Originally, using mp_restartgame used to set the teams' tournament state to ready (and hence would trigger the plugin). However, this was changed at some point in the past.
    This convar gives you the option of whether to start a log when mp_restartgame is used or not.

    Setting this convar to "1" will make it so that logs are ONLY started when teams READY UP using F4. Setting it to "0" will cause new logs to be started on mp_restartgame, provided mp_tournament 
    is enabled, as well as ready up.


livelogs_enable_debugging - Enable/disable debug messages.


livelogs_enabled - Enable/disable Livelogs.

If you have any queries, please do not hesitate to contact me on IRC (_bladez@bladezz.admin.ipgn), or on the ozfortress forums (bladez).