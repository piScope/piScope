from __future__ import print_function

'''
    client.py


    it provides server/client operation of piScope

    A user can launch piScope from any python console,
    and send/recieve various command/data.

    useage:

        from ifigure.client import *

        launch()        # this launch piScope as a separate process
        plot(range(30)) # send range(30) to piscope and make a plot

        ## here a user export plot data to piScope shell, and
        ## create xdata and ydata

        print xdata     # in server/client mode, the data is automatically
                        # sent

        ## a user can also get any pickable variables in piScope shell
        get('varname')

'''

import socket
import subprocess
import sys
import shlex
import ifigure.utils.pickle_wrapper as cPickle
import binascii
import threading
import os
import queue
import signal
import readline
import warnings

from six.moves import socketserver
from ifigure.utils.cbook import pick_unused_port


# async_print
#
#  show message in Python interpromt w/o destroying what is shown now.
#  currnet_prompt stores the last prompt used by Interpreter

current_prompt = ">>> "
_pyrepl_readline = None

if sys.version_info >= (3, 13) and not os.environ.get("PYTHON_BASIC_REPL"):
    try:
        from _pyrepl import readline as pyrepl_readline
    except ImportError:
        pass
    else:
        _pyrepl_readline = pyrepl_readline
        warnings.warn(
            "For Python 3.13 and later, CPython's private _pyrepl API is used to "
            "preserve input during asynchronous piScope output; this may "
            "change in a future Python release.",
            RuntimeWarning,
            stacklevel=2,
        )


class TrackingPrompt:
    def __init__(self, text, primary=False):
        self.text = str(text) if text is not None else '>>> '
        #self.primary = primary

    def __str__(self):
        global current_prompt
        #if self.primary:
        #    current_prompt = self.text
        return self.text


def install_prompt_tracking():
    """Initialize prompt tracking only in real interactive sessions.

    Scripts run with ``python script.py`` do not define ``sys.ps1`` and
    ``sys.ps2``. We must not touch those attributes unconditionally because that
    breaks imports and can misclassify script mode as interactive.
    """
    global current_prompt
    existing_ps1 = getattr(sys, 'ps1', None)
    existing_ps2 = getattr(sys, 'ps2', None)
    sys.ps1 = TrackingPrompt(str(existing_ps1) if existing_ps1 is not None else '>>> ', primary=True)
    sys.ps2 = TrackingPrompt(str(existing_ps2) if existing_ps2 is not None else '... ', primary=False)
    current_prompt = '>>> '


def async_print(*args, **kwargs):
    """
    Print without permanently destroying the line currently being typed
    at the interactive prompt.
    """
    # Save current typed text.
    if _pyrepl_readline is not None:
        buf = _pyrepl_readline.get_line_buffer()
    else:
        buf = readline.get_line_buffer()

    # Move to beginning of line and clear it.
    sys.stdout.write("\r\033[2K")
    sys.stdout.flush()

    print(*args, **kwargs)

    # Redraw prompt + current input.
    sys.stdout.write(current_prompt + buf)
    sys.stdout.flush()

#
#  ReceiverReqHandler : receive data from piscope and send message to main thread
#  using signal
#

class ReceiverReqHandler(socketserver.BaseRequestHandler):
    def handle(self):
        rfile = self.request.makefile('r')
        response = rfile.readline().strip()
        rfile.close()
        data = cPickle.loads(binascii.a2b_hex(response))
        if data['type'] == 'data':
            import __main__
            text = '\n'
            for key in data['data'][0]:
                if key in dir(__main__):
                    text = text + key + ' is updated. \n'
                else:
                    text = text + key + ' is created. \n'
                setattr(__main__, key, data['data'][0][key])
            self.server.msg_queue.put(text)
        elif data['type'] == 'msg':
            self.server.msg_queue.put((data['data']))
        else:
            self.server.msg_queue.put("")
        os.kill(os.getpid(), signal.SIGUSR1)

class Receiver(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msg_queue = queue.Queue()

class Client(object):
    port = 0
    host = 'localhost'
    process = None
    receiver = None

    def launch(self, host='localhost', exe=None):
        if host == 'localhost':
            from ifigure.utils.get_ifigure_dir import bin_dir
            # command = os.path.join(bin_dir(), 'piscope.sh') + ' -s'
            if exe is None:
                exe = sys.executable
            # command = command + ' -e '+ exe + ' &'
            # import piscope
            # command = sys.executable + ' ' + piscope.__file__ + ' -s -d'
            # command = 'piscope  -s -d'
            command = [sys.executable, '-m', 'ifigure', '-s', '-d']            
            if os.altsep is not None:
                command = command.replace(os.sep, os.altsep)
            p = subprocess.Popen(command, #shlex.split(command),  # shell = True,
                                 stdout=subprocess.PIPE,
                                 universal_newlines=True)

            lhost = 'localhost'
        else:
            pass
        line = ''
        while line[0:5] != 'start':
            line = p.stdout.readline()
            print(line)
        arr = line.split(':')
        Client.host = arr[1].rstrip("\r\n").strip()
        Client.port = int(arr[2].rstrip("\r\n").strip())
        Client.process = p
        if Client.receiver is None:
            port = pick_unused_port()

            sys.stdout.flush()
            Client.receiver = Receiver((lhost, port), ReceiverReqHandler)

            server_thread = threading.Thread(
                target=Client.receiver.serve_forever)
            server_thread.daemon = True
            server_thread.start()

        signal.signal(signal.SIGUSR1, self.signal_handler)

        ip, port = Client.receiver.server_address
        print(('receiver :', ip, ':', port))
        message = cPickle.dumps(('r', ip, port))
        self.send(message, noresponse=True)

    def signal_handler(self, signum, frame):
        # This handler executes in Python's main thread.
        while True:
            try:
                msg = Client.receiver.msg_queue.get_nowait()
                async_print(msg)
                Client.receiver.msg_queue.task_done()
            except queue.Empty:
                break

    def shutdown(self):
        if Client.process is not None:
            try:
                Client.process.kill()
            except Exception:
                pass
            Client.process = None
            Client.host = 'localhost'
            Client.port = 0

        if Client.receiver is not None:
            try:
                Client.receiver.shutdown()
            except Exception:
                pass
            Client.receiver = None

    def set_connection(self, host, port):
        Client.port = port
        Client.host = host

    def send(self, message, noresponse=False):
        host = Client.host
        port = Client.port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        response = None
        try:
            hexmessage = binascii.b2a_hex(message)
            sock.sendall(hexmessage + b'\n')
            if not noresponse:
                rfile = sock.makefile('r')
                response = rfile.readline().strip()
                rfile.close()
#             response = sock.recv(1024)
#             print len(response)
                response = cPickle.loads(binascii.a2b_hex(response))
        finally:
            sock.close()

        return response

def launch(exe=None):
    server('launch', exe=exe)


def shutdown():
    server('shutdown')

def server(param, host='localhost', port=None, exe=None):
    '''
    launch/connect piscope
    server('coonect', host, port)
    server('launch')
    server('shutdown')
    '''
    c = Client()
    
    if c.process is not None:
        status = c.process.poll()
        if status is not None:
            print(f"piScope process has already exited with exit code: {status}")
            return
    
    if param == 'launch':
        c.launch(exe=exe)
    if param == 'connect':
        c.set_connection(host, port)
    if param == 'shutdown':
        if c.host is None:
            return
        if c.port == 0:
            return

        message = cPickle.dumps(('f', 'quit', tuple(), dict()))
        c.send(message, noresponse=True)
        c.shutdown()
    print(('host: ', c.host, ', port: ', c.port))


def check_connection():
    c = Client()
    message = cPickle.dumps(('c',))
    print((c.send(message)))


def make_testplot():
    execute('plot(range(10))')


def execute(source):
    """Execute Python source in piScope's shell namespace."""
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    message = cPickle.dumps(('t', source))
    c = Client()
    return c.send(message)


def _get_random_name():
    # get random name
    from time import gmtime, strftime
    import hashlib
    import os
    import ifigure_config

    check = True
    while(check):
        strtime = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        m = hashlib.md5()
        m.update(strtime)
        txt = m.hexdigest()
        fpath = os.path.join(ifigure_config.rcdir,
                             '###param_'+txt)
        check = os.path.exists(fpath)
    return fpath


def _save_parameter_file(*args, **kargs):
    try:
        return sr
    except IOError as error:
        return False


def _send_message(command, *args, **kargs):
    try:
        message = cPickle.dumps(('f', command, args, kargs))
    except error:
        print('failed to save parameter file')
        return
    c = Client()
    return c.send(message)


def _send_message_g(command, *args, **kargs):
    try:
        message = cPickle.dumps(('g', command, args, kargs))
    except error:
        print('failed to save parameter file')
        return
    c = Client()
    return c.send(message)

def _send_message_d():
    try:
        message = cPickle.dumps(('d', ))
    except error:
        print('failed to save parameter file')
        return
    c = Client()
    return c.send(message)

names = ['figure',
         'showpage', 'cla', 'cls', 'clf', 'nsec', 'nsection',
         'subplot', 'isec', 'isection', 'addpage', 'delpage',
         'suptitle', 'title',
         'xlabel', 'xtitle', 'ylabel', 'ytitle', 'zlabel', 'ztitle',
         'clabel', 'ctitle',
         'xlog', 'ylog', 'clog', 'zlog',
         'xsymlog', 'ysymlog', 'zsymlog', 'csymlog',
         'xlinear', 'ylinear', 'clinear', 'zlinear',
         'xauto', 'yauto', 'zauto', 'cauto',
         'xlim', 'ylim', 'zlim', 'clim',
         'twinx', 'twiny',
         'oplot', 'oerrorbar',
         'loglog', 'semilogy', 'semilogx',
         'timetrace', 'plotc', 'errorbarc',
         'plot', 'scatter', 'hist', 'triplot', 'errorbar', 'annotate',
         'ispline', 'contour', 'contourf', 'quiver', 'quiver3d',
         'image', 'specgram', 'spec', 'tripcolor', 'tricontour',
         'tricontourf', 'axline', 'axlinec', 'axspan', 'axspanc',
         'text', 'figtext', 'arrow', 'figarrow', 'legend', 'fill',
         'fill_between', 'fill_betweenx', 'fill_between_3d', 'surf',
         'surface', 'revolve', 'solid', 'trisurf', 'property', 'threed',
         'lighting','view',
         'xnames', 'ynames', 'znames', 'cnames',
         'cbar', 'savefig', 'savedata',
         ]

for name in names:
    def f(*args, _name=name,  **kargs):
        _send_message(_name, *args, **kargs)
    globals()[name] = f

def get(*args, **kargs):
    return _send_message_g('get_shellvar', *args, **kargs)


def put(*args, **kargs):
    return _send_message_g('pet_shellvar', *args, **kargs)

def detach():
    return _send_message_d()

#
#  handle process exiting
#
import atexit
def _is_interactive_session():
    """Return True only for actual interactive Python sessions.

    A plain script run from a terminal still has a TTY, but it does not have
    REPL prompt attributes like ``sys.ps1`` / ``sys.ps2`` and is not launched
    with ``python -i``. Treating any TTY as interactive causes script mode to
    register ``atexit`` cleanup and immediately kill the piScope process.
    """
    if hasattr(sys, 'ps1') or hasattr(sys, 'ps2'):
        return True

    flags = getattr(sys, 'flags', None)
    if flags is not None:
        try:
            return bool(flags.interactive)
        except Exception:
            pass

    return False


if _is_interactive_session():
    install_prompt_tracking()
    atexit.register(shutdown)
else:
    current_prompt = '>>> '
    atexit.register(detach)

# launch piScope whne from ifigure.client import * is called.
launch()
