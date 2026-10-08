
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
import time
import shlex
from ifigure._private.interactive_common import COMMON_API
import pickle
import binascii
import threading
import os
import queue
import signal
import readline
import warnings

import socketserver
from ifigure.utils.cbook import pick_unused_port
import ifigure.utils.pid_exists


_PROXY_MARKER = '__ifigure_proxy__'


def _unwrap_proxy(value):
    if isinstance(value, dict):
        if _PROXY_MARKER in value and len(value) == 1:
            return FigureProxy(value[_PROXY_MARKER])
        return {k: _unwrap_proxy(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return tuple(_unwrap_proxy(v) for v in value)
    if isinstance(value, list):
        return [_unwrap_proxy(v) for v in value]
    return value


class FigureProxy(object):
    def __init__(self, object_path):
        self.object_path = object_path

    def __repr__(self):
        return 'FigureProxy(%s)' % (self.object_path,)

    def _call(self, name, *args, **kargs):
        kargs['_object_path'] = self.object_path
        return _send_message(name, *args, **kargs)

    def _call_g(self, name, *args, **kargs):
        kargs['_object_path'] = self.object_path
        kargs['_return_proxy'] = True
        return _unwrap_proxy(_send_message_g(name, *args, **kargs))

    def get_page(self, ipage=None):
        return self._call_g('get_page', ipage=ipage)

    def get_axes(self, ipage=None, iaxes=None):
        return self._call_g('get_axes', ipage=ipage, iaxes=iaxes)

    def ax_getaxes(self, ipage=None, iaxes=None):
        return self.get_axes(ipage=ipage, iaxes=iaxes)

    def ax_getpage(self, ipage=None):
        return self.get_page(ipage=ipage)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)

        def _method(*args, **kargs):
            return _unwrap_proxy(_send_message_g(
                name, *args, _object_path=self.object_path,
                _return_proxy=True, **kargs))

        return _method


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
        data = pickle.loads(binascii.a2b_hex(response))
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

            if exe is None:
                exe = sys.executable

            # -d option increase pytest failour rate.
            #command = [exe, '-m', 'ifigure', '-s', '-q', '-d', '-n']
            command = [exe, '-m', 'ifigure', '-s', '-q', '-n']
            if os.altsep is not None:
                command = command.replace(os.sep, os.altsep)
            p = subprocess.Popen(command, #shlex.split(command),  # shell = True,
                                 stdout=subprocess.PIPE,
                                 universal_newlines=True)
            Client.process = p
        else:
            pass
            ## To Do launch piScope on remote session (perhaps not necessary)
        line = ''
        while line[0:5] != 'start':
            line = p.stdout.readline()
            if not line:
                status = p.poll()
                if status is not None:
                    raise RuntimeError(
                        f"piScope process exited before starting its server "
                        f"(exit code {status})"
                    )
        arr = line.split(':')
        Client.host = arr[1].rstrip("\r\n").strip()
        Client.port = int(arr[2].rstrip("\r\n").strip())

        if Client.receiver is None:
            self._start_receiver('localhost')

        signal.signal(signal.SIGUSR1, self.signal_handler)

        '''
        # this is a safeguard to make sure that piScope is ready to
        # communicate. it seems we don't need it.
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            try:
                # Use a valid protocol request so server-side handlers do not
                # see an empty payload while we probe readiness.
                self.send(pickle.dumps(('c',)))
                break
            except OSError:
                time.sleep(0.1)
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError(
                f"piScope server did not become ready on {Client.host}:{Client.port} "
                f"within 10 seconds"
            )
        '''
        ip, port = Client.receiver.server_address
        message = pickle.dumps(('r', ip, port))
        self.send(message, noresponse=True)
        return Client.port, p.pid

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

        if Client.receiver is None:
            self._start_receiver('localhost')

        signal.signal(signal.SIGUSR1, self.signal_handler)

        ip, port = Client.receiver.server_address
        message = pickle.dumps(('r', ip, port))
        self.send(message, noresponse=True)

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
                response = pickle.loads(binascii.a2b_hex(response))
        finally:
            sock.close()

        return response

    def _start_receiver(self, lhost):
        port = pick_unused_port()

        sys.stdout.flush()
        Client.receiver = Receiver((lhost, port), ReceiverReqHandler)

        server_thread = threading.Thread(target=Client.receiver.serve_forever)
        server_thread.daemon = True
        server_thread.start()


def _ensure_connection():
    if Client.port == 0 or Client.process is None:
        launch()


def launch(exe=None):
    """Launch piScope and return its server port and process ID."""
    return _server_control('launch', exe=exe)


def shutdown():
    _server_control('shutdown')

def connect(port, host='localhost'):
    _server_control('connect', host, port)

def _server_control(param, host='localhost', port=None, exe=None):
    '''
    launch/connect piscope
    server('coonect', host, port)
    server('launch')
    server('shutdown')
    '''
    c = Client()


    if param == 'launch':
        return c.launch(exe=exe)
    if param == 'connect':
        c.set_connection(host, port)
        return
    if param == 'shutdown':
        if c.host is None:
            return
        if c.port == 0:
            return

        message = pickle.dumps(('f', 'quit', tuple(), dict()))

        if c.process is not None and ifigure.utils.pid_exists.pid_exists(c.process.pid):
            c.send(message, noresponse=True)
        else:
            print("piScope process has already exited")
        c.shutdown()


def check_connection():
    c = Client()
    message = pickle.dumps(('c',))
    print((c.send(message)))


def make_testplot():
    execute('plot(range(10))')


def execute(source):
    """Execute Python source in piScope's shell namespace."""
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    message = pickle.dumps(('t', source))
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


def _send_message(command, *args, **kargs):
    _ensure_connection()
    try:
        message = pickle.dumps(('f', command, args, kargs))
    except BaseException:
        print('failed to save parameter file')
        return
    c = Client()
    return c.send(message)


def _send_message_g(command, *args, **kargs):
    _ensure_connection()
    try:
        message = pickle.dumps(('g', command, args, kargs))
    except BaseException:
        print('failed to save parameter file')
        return
    c = Client()
    return c.send(message)

def _send_message_d():
    if Client.port == 0 or Client.process is None:
        return None
    try:
        message = pickle.dumps(('d', ))
    except BaseException:
        print('failed to save parameter file')
        return
    c = Client()
    return c.send(message)

for name in COMMON_API:
    if name == 'property':
        def f(*args, _name=name, **kargs):
            return _send_message_g(_name, *args, **kargs)
    else:
        def f(*args, _name=name, **kargs):
            _send_message(_name, *args, **kargs)
    globals()[name] = f


def figure(*args, **kargs):
    proxy = _send_message_g('figure', *args, _return_proxy=True, **kargs)
    if proxy is None:
        return None
    return _unwrap_proxy(proxy)


def server(*args, **kargs):
    return _send_message('server', *args, **kargs)

def get(*args, **kargs):
    return _send_message_g('get_shellvar', *args, **kargs)


def put(*args, **kargs):
    return _send_message_g('pet_shellvar', *args, **kargs)

def detach():
    try:
        return _send_message_d()
    except Exception:
        return None

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


def _is_main_thread():
    try:
        return threading.current_thread() is threading.main_thread()
    except Exception:
        return True


if _is_interactive_session() and _is_main_thread():
    # launch piScope whne from ifigure.client import * is called.    
    launch()
    install_prompt_tracking()
    atexit.register(shutdown)
else:
    current_prompt = '>>> '
    atexit.register(detach)

