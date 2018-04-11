echo Windows command script to start piscope
echo Warning: my windows scripting skills are old and were never very good

echo If this command returns an ip address, it should be used instead of localhost
echo so either http://localhost:6080 or http://ip:6080

docker-machine ip 

echo Trying to remove old instances of container
docker rm piscope-instance
docker stop piscope-instance

echo Starting piscope container as image piscope-instance
docker run -d --name piscope-instance -v %HOMEPATH%:/home/user/ssh_mount -v %CD%:/home/user/work -p 6080:6080 jcwright/piscope

echo Remove instance after exiting
docker stop piscope-instance
docker rm piscope-instance

