#!/bin/sh

# was but removed because of docker-machine use
# script_dir="`cd $(dirname $0); pwd`"
# $script_dir/run_base.sh  -c piscope-example -i jcwright/piscope -v ~/.ssh:/home/user/.ssh -p 6080  "$@"

echo \'Nix command script to start piscope

echo If this command returns an ip address, it should be used instead of localhost
echo so either http://localhost:6080 or http://ip:6080

docker-machine ip 

echo Trying to remove old instances of container
docker rm piscope-instance
docker stop piscope-instance

echo Starting piscope container as image piscope-instance
docker run -d --name piscope-instance -v $HOME/.ssh:/home/user/ssh_mount -v $PWD:/home/user/work -p 6080:6080 jcwright/piscope



