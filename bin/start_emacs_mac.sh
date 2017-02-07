#!/bin/sh
# derived from start_emacs.sh it add two alias
alias emacsclient="/Applications/Emacs.app/Contents/MacOS/bin/emacsclient"
alias emacsd="/Applications/Emacs.app/Contents/MacOS/Emacs --daemon"

ANS=`emacsclient -e '(<= 2 (length (visible-frame-list)))' 2> /dev/null || echo "fail"`
if [ $ANS == "fail" ]; then
    emacsd
fi
ANS=`emacsclient -e '(<= 2 (length (visible-frame-list)))' || echo "fail"`
if [ $ANS != "t" ]; then
    emacsclient -n -c -a ""
fi
emacsclient -n -a "" "$@"
