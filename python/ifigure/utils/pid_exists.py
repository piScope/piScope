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
        from win32con import STILL_ACTIVE, PROCESS_ALL_ACCESS

        process = kernel32.OpenProcess(PROCESS_ALL_ACCESS, 0, pid)

        if not process:
            return False
        ec = DWORD(0)
        out = kernel32.GetExitCodeProcess(process, ctypes.pointer(ec))#ctypes.byref(ec))
        if not out:
            err = kernel32.GetLastError()
            if kernel32.GetLastError() == 5:
                # Access is denied.
                logging.warning("Access is denied to get pid info." + str(pid))
            kernel32.CloseHandle(process)
            return True
        elif ec != DWORD(STILL_ACTIVE):
            # If the error code (ec) is not STILL_ACTIVE..
            # There is an exist code, it quit
            kernel32.CloseHandle(process)
            return False
        # No exit code, it's running.
        kernel32.CloseHandle(process)
        return True
