#!/bin/sh
###
###  piscope 
###
###    start up script for piescope
###    usage : piscope -e {exec} {file}
INTERPRETER=`which python2.7`
COM='""'
#
#
#
_usage() {
    echo 'piscope : interactive ploting GUI on matplotlib'
    echo '   usage : piscope [-s] [-r command] [-e exec] [file]'
    echo '   -e : (optional) : python interpreter executable'
    echo '   -s : (optional) : start server'
    echo '   -c : (optional) : use consol'
    echo '   -d : (optional) : redirect output'
    echo '   -p : (optional) : launch profiler at startup'
    echo '   -r : (optional) : execute python command in shell'
    echo '   -n : (optional) : no main window'
    echo '   file: (optional) : .bfz or .pfz file to open'
    exit 1
}

EXTRA=''
EXTRA2=''
EXTRA3=''
EXTRA4=''
while getopts "r:e:f:sdchpn" opts
do 
   case $opts in
      e) INTERPRETER=$OPTARG
         ;;
      r) COM=$OPTARG
         ;;
      s) EXTRA='-s'
         ;;
      d) EXTRA2='-d'
         ;;
      c) EXTRA2='-c'
         ;;
      p) EXTRA3='-p'
         ;;
      n) EXTRA4='-n'
         ;;
      h) _usage;;
      :|\?) _usage;;
   esac
done

#echo $@
#echo ${@:1:$((OPTIND-1))}
shift `expr ${OPTIND} - 1`

ME=`python -c "import os,sys;print os.path.realpath('$0')"`
#ME=$(`python -c 'import os,sys;print os.path.realpath(sys.argv[1])' $0`)
echo $ME
MEDIR=$(dirname $ME)
DIR=$(dirname $MEDIR)

APP=$DIR/python/piscope.py
$INTERPRETER $APP $EXTRA $EXTRA2 $EXTRA3 $EXTRA4 $1

# following is an attempt to launch piscope from app folder
# it is not straighforward to go this option.
# main problem is an enviroment (pythonpath) should be
# set up correctly to use this option.
# This makes it complicate to make "open project in new piscope"
# work, since when a user chooose this from menu, the program
# does not do this extra step.
#export PYTHONPATH=$DIR/python:$PYTHONPATH
#APP=$DIR/macapplet/dist/piscope.app/Contents/MacOS/piscope
#$APP $EXTRA $EXTRA2 $EXTRA3 $EXTRA4 $1
