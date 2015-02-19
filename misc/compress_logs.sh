LOGDIR="/data/livelogs/logs"

function compress_if_unused {
    INUSE=`/bin/fuser $1`
    if [[ -z "$INUSE" ]]; then
        # if not in use, COMPRESS
        echo "$1 is not in use. compressing"
        /bin/gzip $1
        #echo $1
    fi
}

export -f compress_if_unused

/usr/bin/find $LOGDIR -type f -iname "*.log" -exec bash -c 'compress_if_unused "$0"' {} \;
