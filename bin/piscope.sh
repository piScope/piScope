#!/bin/bash
###
###  piscope 
###
###    start up script for piescope
###    usage : piscope -e {exec} {file}
INTERPRETER=`which python`

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
    echo '   -g : (optional) : open off GL'
    echo '   -k : (optional) : use open GL (LIBGL_ALWAYS_SOFTWARE=1)'    
    echo '   -u : (optional) : unsuppress Gtk-warning'
    echo '   file: (optional) : .bfz or .pfz file to open'
    exit 1
}

EXTRA=''
EXTRA2=''
EXTRA3=''
EXTRA4=''
while getopts "r:e:f:sdchpngku" opts
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
      g) EXTRA5='-g'
         ;;
      k) export LIBGL_ALWAYS_SOFTWARE=1
         ;;
      u) UNSUPPRESS_GTK=1	     
         ;;
      h) _usage;;
      :|\?) _usage;;
   esac
done

#echo $@
#echo ${@:1:$((OPTIND-1))}
shift `expr ${OPTIND} - 1`

ME=`python -c "import os,sys;print(os.path.realpath('$0'))"`
#ME=$(`python -c 'import os,sys;print os.path.realpath(sys.argv[1])' $0`)
echo $ME
#echo $DYLD_LIBRARY_PATH ## On MacOS El Capitan, this is not carried if
                         ## #!/bin/bash -l is not used....
MEDIR=$(dirname $ME)
DIR=$(dirname $MEDIR)

#export PYTHONPATH=$DIR/python:$PYTHONPATH
#APP=$DIR/python/ifigure/piscope.py

# python add script directory in search path 
APP=$DIR/python/piscope.py

if ! [ -x "$(command -v unbeffer)" ]; then
   $INTERPRETER $APP $EXTRA $EXTRA2 $EXTRA3 $EXTRA4 $EXTRA5 -r $COM $1
else
   if [ -z ${UNSUPPRESS_GTK+x} ];then
       unbuffer $INTERPRETER $APP $EXTRA $EXTRA2 $EXTRA3 $EXTRA4 $EXTRA5 -r $COM $1 2>&1 | unbuffer -p grep -v "Gtk-" | unbuffer -p grep -v -e "^$"
   else
       $INTERPRETER $APP $EXTRA $EXTRA2 $EXTRA3 $EXTRA4 $EXTRA5 -r $COM $1
   fi
fi

 
