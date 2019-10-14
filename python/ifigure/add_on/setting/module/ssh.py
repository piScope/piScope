from __future__ import print_function
#
#   Obsolete module (use connection module)
#
import subprocess
import wx
import os
import shlex
import socket

module_name = 'SSH'
class_name = 'SSH'
menu = [("Connect",    "onOpen",    False),
        ("Disconnect", "onClose",  False),
        ("Send",       "onSend",  False),
        ("Recieve",    "onRec",  False),
        ("Exec",       "onExec",  False),
        ("Setting...", "onSetting",  False)]
method = ['clean', 'setSetting', 'onSetting',
          'onOpen', 'onClose', 'onSend',
          'onRec', 'onExec']
icon = 'world_link.png'
can_have_child = False
has_private_owndir = False


def scp_paramiko(localhost, port, lfile, rfile):

    import paramiko
#  username = ('user')
#  password = ('1234')
    hostname = localhost
    ports = port
    localD = (lfile)
    remoteD = (rfile)

    paramiko.util.log_to_file('/tmp/paramiko.log')
    transport = paramiko.Transport(('localhost', 10001))
    transport.connect()
    sftp = paramiko.SFTPClient.from_transport(transport)
    sftp.put(remotepath=remoteD, localpath=localD)

    sftp.close()
    transport.close()


def pick_unused_port():
    '''
    a routeint to le a system to pick an unused port.
    this recipe was found in active state web site
    '''
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    addr, port = s.getsockname()
    s.close()
    return port


def set_td_var(td, server=None, port=None,
               rport=None, mode=None,
               rserver=None):
    if server is not None:
        td.setvar("server", str(server))
    if port is not None:
        td.setvar("port", int(port))
    if rport is not None:
        td.setvar("rport", int(rport))
    if mode is not None:
        td.setvar("mode", str(mode))
    if rserver is not None:
        td.setvar("rserver", str(rserver))


def get_td_var(td):
    server = td.getvar("server")
    port = td.getvar("port")
    rport = td.getvar("rport")
    mode = td.getvar("mode")
    rserver = td.getvar("rserver")
    return server, port, rport, mode, rserver


def clean(self):
    # clean is a special process called when td is deleted
    if hasattr(self, 'p'):
        self.p.terminate()
        del self.p


def setSetting(self, value):
    rserver = value[4]
    if value[1] == 'loki':
        rserver = 'loki.psfc.mit.edu'

    set_td_var(self.td, server=str(value[4]),
               port=str(value[2]),
               rport=str(value[3]),
               mode=str(value[1]),
               rserver=rserver)
    self.td._name = str(value[1])
    self.td._status = 'not connected'

    app = self.td.get_root_parent().app
    app.proj_tree_viewer.update_widget()


def onRec(self, file=None, rfile=None, rdir=None):
    if rfile is None:
        print("please specify remote file")
        return
    if rdir is not None:
        rfile = os.path.join(rdir, rfile)
    m = self

    if file == None:
        file = os.path.join(os.getcwd(),
                            str(os.path.basename(rfile)))

    server, port, rport, mode, rserver = get_td_var(self.td)
    command = 'scp -P '+str(port) + ' localhost:'+rfile + ' '+file
    print(command)
    p = subprocess.Popen(shlex.split(command), stderr=subprocess.STDOUT,
                         stdout=subprocess.PIPE)
    p.wait()
    print(('stdout', p.stdout.read()))


def onExec(self, e=None, command=None, wait=True):
    if command is None:
        return
    server, port, rport, mode, rserver = get_td_var(self.td)

    command = 'ssh -p '+str(port) + ' localhost ' + command

    p = subprocess.Popen(shlex.split(command), stderr=subprocess.STDOUT,
                         stdout=subprocess.PIPE)

    if wait:
        while p.wait() == None:
            wx.SafeYield()
            time.sleep(0.25)
    print(('stdout', p.stdout.read()))


def onSend(self, file=None, rdir=None, rfile=None):
    if self.td._status != 'connected':
        print("SSH conection is not established")
        return

    if file is None:
        open_dlg = wx.FileDialog(None,
                                 message="Select file to send",
                                 style=wx.FD_SAVE)
        if open_dlg.ShowModal() != wx.ID_OK:
            open_dlg.Destroy()
            return
        file = open_dlg.GetPath()
        open_dlg.Destroy()

    rfile = str(os.path.basename(file))
    rdir = str(rdir)
    if rdir is not None:
        rfile = os.path.join(rdir, rfile)

    server, port, rport, mode, rserver = get_td_var(self.td)

    command = 'ssh -p '+str(port) + ' localhost mkdir ' + rdir

    p = subprocess.Popen(shlex.split(command), stderr=subprocess.STDOUT,
                         stdout=subprocess.PIPE)

    p.wait()
    print(('stdout', p.stdout.read()))

    #scp_paramiko('localhost', port, file, rfile)

    command = 'scp -P '+str(port) + ' '+str(file) + ' localhost:'+rfile
    print(command)
    subprocess.Popen(command, shell=True)
    print(p.wait())


def onClose(self):
    if hasattr(self, 'p'):
        self.p.terminate()
        del self.p
    self.td._name = self.td.getvar("mode")
    self.td._status = 'not connected'
    app = self.td.get_root_parent().app
    app.proj_tree_viewer.update_widget()


def onOpen(self):
    import subprocess
    import shlex
    import wx
    if hasattr(self, 'p'):
        self.p.terminate()
        del self.p

    m = self
    server, port, rport, mode, rserver = get_td_var(self.td)

    command = 'ssh -N '+str(server) + ' -L ' +  \
        str(port)+':' + str(rserver)+':' + \
        str(rport)
    print(command)
    self.p = subprocess.Popen(shlex.split(command))
    self.td._name = self.td.getvar("mode")
    self.td._status = 'connected'
    app = self.td.get_root_parent().app
    app.proj_tree_viewer.update_widget()


def onSetting(self):
    server, port, rport, mode, rserver = get_td_var(self.td)

    if port is None:
        port = str(10000)
    if server is None:
        server = 'cmodws60.psfc.mit.edu'
    if rport is None:
        rport = '22'
    if mode is None:
        mode = 'loki'
    list = [["", "SSH connection", 2],
            ["SSH connection", mode, 4,
             {"choices": ["loki", "MDSPlus_CMOD", "pyro_ns"]}],
            ["local port", str(port), 0],
            ["remote port", str(rport), 0],
            ["sever", server, 0]]

    app = self.td.get_root_parent().app
    app.proj_tree_viewer.OpenPanel(list, self, 'setSetting')
