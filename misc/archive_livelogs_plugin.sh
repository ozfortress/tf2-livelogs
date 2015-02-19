#!/bin/bash

PLUGIN_WEB_DIR=/var/www/livelogs/live/plugindata

cd $PLUGIN_WEB_DIR

/bin/tar cfvhj livelogs.tar.bz2 scripting plugins extensions readme.txt GPLv3.txt
