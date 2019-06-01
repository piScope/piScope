'''
   pid_exits

   based on Q&A in 
   http://stackoverflow.com/questions/568271/how-to-check-if-there-exists-a-process-with-a-given-pid
 

   however, if access is denied, it returns True. 
'''
import os
import logging


def pid_exists(pid):
    """Check whether pid exists in the current process table."""
    if os.name == 'posix':
        import errno
        if pid < 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError as e:
            return e.errno == errno.EPERM
        else:
            return True
    else:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        HANDLE = ctypes.c_void_p
        DWORD = ctypes.c_ulong
        LPDWORD = ctypes.POINTER(DWORD)

        class ExitCodeProcess(ctypes.Structure):
            _fields_ = [('hProcess', HANDLE),
                        ('lpExitCode', LPDWORD)]
        SYNCHRONIZE = 0x100000
        process = kernel32.OpenProcess(SYNCHRONIZE, 0, pid)

        if not process:
            return False
        ec = ExitCodeProcess()
        out = kernel32.GetExitCodeProcess(process, ctypes.byref(ec))
        if not out:
            err = kernel32.GetLastError()
            if kernel32.GetLastError() == 5:
                # Access is denied.
                logging.warning("Access is denied to get pid info." + str(pid))
            kernel32.CloseHandle(process)
            return True
        elif bool(ec.lpExitCode):
            # print ec.lpExitCode.contents
            # There is an exist code, it quit
            kernel32.CloseHandle(process)
            return False
        # No exit code, it's running.
        kernel32.CloseHandle(process)
        return True
