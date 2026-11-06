"""Windows-Ersatz für das Unix-Modul fcntl (nur flock).

Wird nur importiert, wenn `import fcntl` fehlschlägt. Das eingebettete
Agent-Terminal (pty/termios) gibt es unter Windows nicht.
"""
import msvcrt
import os
import time
import types

LOCK_SH, LOCK_EX, LOCK_NB, LOCK_UN = 1, 2, 4, 8


def _fd(handle):
    return handle if isinstance(handle, int) else handle.fileno()


def flock(handle, operation):
    fd = _fd(handle)
    position = os.lseek(fd, 0, os.SEEK_CUR)
    os.lseek(fd, 0, os.SEEK_SET)
    try:
        if operation & LOCK_UN:
            try:
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        elif operation & LOCK_NB:
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except OSError as error:
                raise BlockingIOError(str(error))
        else:
            while True:
                try:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
    finally:
        os.lseek(fd, position, os.SEEK_SET)


fcntl = types.SimpleNamespace(
    LOCK_SH=LOCK_SH, LOCK_EX=LOCK_EX, LOCK_NB=LOCK_NB, LOCK_UN=LOCK_UN, flock=flock)
