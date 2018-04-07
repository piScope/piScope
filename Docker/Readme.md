Instructions for launching piscope and petram via a docker container.

- First install Docker for your platform. See http://docker.com

    For windows 10 professional and enterprise users, install the
    community addition. This will require admin access. After
    installation, add yourself to the docker-users group. The first 
    time DOcker mounts a local volume of opens a port (eg for VNC) you 
    will be asked to authorized as well.

    For windows 10 home, install Docker Toolbox which uses virtualbox
    (which is installed for you.) See

      https://docs.docker.com/toolbox/toolbox_install_windows/

    This installation will not require permissions for firewall ports 
    or local volumes as this is done through a lightweight virtualbox
    image. Otherwise, the commands are the same but you access through
    a dedicated MINGW64 prompt via the "Docker Quickstart" program/icon.
    Containers will also be accessed through the VirtualBox shared network
    rather than localhost, typically something like `http://192.168.99.100:6082/`


- Copy the Dockerfile.* files to a directory to build the images.
   Container images can be run  from any directory after they are built. 
   When building Dockerfile.petram, define the environmental variable `GITAUTH`
   for access the currently private PetraM repository of the form
   `username:password` or just provide it on the command line in place
   of  `${GITAUTH}`.

   Run:

      docker build -t jcwright/wxpython-base -f Dockerfile.wxpython-base .
      docker build -t jcwright/piscope -f Dockerfile.piscope .
      docker build -t jcwright/petram --build-arg GITAUTH=${GITAUTH} -f Dockerfile.petram .

  The last one is optional and not needed to run piscope workflows. Keep
  the namespace preamble (jcwright) because the builds and scripts use
  that namespace.

- Now, set up a working directory in which to run piscope.

  This directory and its contents and subdirectories will be available 
  as the "work" directory in the container.

  To run the image, execute the `run_piscope.cmd` (WIN) or 
  `run_piscope.sh` (NIX) script depending on your platform. Then open
  a browser to indicated network. Note that the `run_base.sh` script
  uses `docker-machine` which is *only* for use on machines that do
  not support native virtualization. Currently linux, OSX and Windows 10
  Enterprise do support native virtualization. 


  These scripts cleanup previous images and deploy a new one. They
  essentially boil down to running this single command:

    docker run -d --name piscope-instance -v $HOME/.ssh:/home/user/.ssh -v $PWD:/home/user/work -p 6080:6080 jcwright/piscope

- Miscellaneous
   The piscope image starts up using the openbox window manager. You
   can change this via the desktop menu through
   Debian->WindowManagers->ICEWm


