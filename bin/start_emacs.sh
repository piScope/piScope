#!/bin/sh

xprop -name emacs >/dev/null 2>/dev/null
if [ "$?" = "1" ]; then
    emacsclient -c -n -a "" "$@"
else
    emacsclient -n -a "" "$@"
fi
