livelogs server plugin README updated 20/2/2015

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



livelogs_new_log_file - Enable/disable the initialisation of logging on match start using 'log on'. 'log on' is required so that logs are output to the server's console, and hence 
    sent to livelogs.
    
    If you are running another plugin that enables logging using 'log on' at some point, this can be disabled if you wish. However, you can still leave it on so that fresh log 
    files are created in your server's log directory for new matches, if you choose to.

    Setting this convar to "1" will use 'log on'. Setting it to "0" will not use 'log on' on match start.

    
livelogs_name - The name that is displayed on the livelogs webpage for logs from your server.


livelogs_tournament_ready_only - Whether to start logging on tournament readies only or not. 
    Originally, using mp_restartgame used to set the teams' tournament state to ready (and hence would trigger the plugin). However, this was changed at some point in the past.
    This convar gives you the option of whether to start a log when mp_restartgame is used or not.

    Setting this convar to "1" will make it so that logs are ONLY started when teams READY UP using F4. Setting it to "0" will cause new logs to be started on mp_restartgame, 
    provided mp_tournament is enabled, as well as ready up.


livelogs_force_logsecret - Whether to force the plugin's log secret or not.
    If your server uses its own sv_logsecret for another service, you should set this to "0", so that the plugin will not change it. If not, this should be left at "1", so that
    your logs will use the plugin's secret and cannot be spoofed.


livelogs_panel - Whether to show a panel when users use !livelogs or not.
    If you want an in-game panel with the log page in it to be displayed alongside a URL, set this to "1". If not, set it to "0" to just display the URL.

livelogs_log_overheal - Whether or not to log overheal as a separate statistic. 
    F2's MedicStats does not treat overhealing as a separate statistic, and instead globs it into standard healing.


livelogs_enable_debugging - Enable/disable debug messages.


livelogs_enabled - Enable/disable Livelogs.



If you have any queries, please do not hesitate to contact me on IRC (_bladez@bladezz.admin.ipgn), or on the ozfortress forums (bladez).


For more information on the SourceMod socket extension, please visit https://forums.alliedmods.net/showthread.php?t=67640
