#!/bin/sh
###
###  mdsplus_gateway
###
###    start up script for piescope
###    usage : piescope -e {exec} {file}
INTERPRETER=`which python`

#
#
#
_usage() {
    echo 'mdsplus_gateway : gateway to MDSplus'
    echo '   usage : mdsplus_gateway [start|stop]'
    exit 1
}


ME=`python -c "import os,sys;print os.path.realpath('$0')"`
#ME=$(`python -c 'import os,sys;print os.path.realpath(sys.argv[1])' $0`)
echo $ME
MEDIR=$(dirname $ME)
DIR=$(dirname $MEDIR)

export PYTHONPATH=$DIR/python:$PYTHONPATH
SCRIPT=$DIR/python/ifigure/mdsplus/mdsplus_gateway.py

$INTERPRETER $SCRIPT $1
more /tmp/mdsplus_gateway.log