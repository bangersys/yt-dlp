
import contextlib
import errno
import functools
import operator
import os
import sys


class LockingUnsupportedError(OSError):
    msg = 'File locking is not supported'

    def __init__(self):
        super().__init__(self.msg)


# Cross-platform file locking
if sys.platform == 'win32':
    import ctypes
    import ctypes.wintypes
    import msvcrt

    class OVERLAPPED(ctypes.Structure):
        _fields_ = [
            ('Internal', ctypes.wintypes.LPVOID),
            ('InternalHigh', ctypes.wintypes.LPVOID),
            ('Offset', ctypes.wintypes.DWORD),
            ('OffsetHigh', ctypes.wintypes.DWORD),
            ('hEvent', ctypes.wintypes.HANDLE),
        ]

    kernel32 = ctypes.WinDLL('kernel32')
    LockFileEx = kernel32.LockFileEx
    LockFileEx.argtypes = [
        ctypes.wintypes.HANDLE,     # hFile
        ctypes.wintypes.DWORD,      # dwFlags
        ctypes.wintypes.DWORD,      # dwReserved
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockLow
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockHigh
        ctypes.POINTER(OVERLAPPED),  # Overlapped
    ]
    LockFileEx.restype = ctypes.wintypes.BOOL
    UnlockFileEx = kernel32.UnlockFileEx
    UnlockFileEx.argtypes = [
        ctypes.wintypes.HANDLE,     # hFile
        ctypes.wintypes.DWORD,      # dwReserved
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockLow
        ctypes.wintypes.DWORD,      # nNumberOfBytesToLockHigh
        ctypes.POINTER(OVERLAPPED),  # Overlapped
    ]
    UnlockFileEx.restype = ctypes.wintypes.BOOL
    whole_low = 0xffffffff
    whole_high = 0x7fffffff

    def _lock_file(f, exclusive, block):
        overlapped = OVERLAPPED()
        overlapped.Offset = 0
        overlapped.OffsetHigh = 0
        overlapped.hEvent = 0
        f._lock_file_overlapped_p = ctypes.pointer(overlapped)

        if not LockFileEx(msvcrt.get_osfhandle(f.fileno()),
                          (0x2 if exclusive else 0x0) | (0x0 if block else 0x1),
                          0, whole_low, whole_high, f._lock_file_overlapped_p):
            # NB: No argument form of "ctypes.FormatError" does not work on PyPy
            raise BlockingIOError(f'Locking file failed: {ctypes.FormatError(ctypes.GetLastError())!r}')

    def _unlock_file(f):
        assert f._lock_file_overlapped_p
        handle = msvcrt.get_osfhandle(f.fileno())
        if not UnlockFileEx(handle, 0, whole_low, whole_high, f._lock_file_overlapped_p):
            raise OSError(f'Unlocking file failed: {ctypes.FormatError()!r}')

else:
    try:
        import fcntl

        def _lock_file(f, exclusive, block):
            flags = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            if not block:
                flags |= fcntl.LOCK_NB
            try:
                fcntl.flock(f, flags)
            except BlockingIOError:
                raise
            except OSError:  # AOSP does not have flock()
                fcntl.lockf(f, flags)

        def _unlock_file(f):
            with contextlib.suppress(OSError):
                return fcntl.flock(f, fcntl.LOCK_UN)
            with contextlib.suppress(OSError):
                return fcntl.lockf(f, fcntl.LOCK_UN)  # AOSP does not have flock()
            return fcntl.flock(f, fcntl.LOCK_UN | fcntl.LOCK_NB)  # virtiofs needs LOCK_NB on unlocking

    except ImportError:

        def _lock_file(f, exclusive, block):
            raise LockingUnsupportedError

        def _unlock_file(f):
            raise LockingUnsupportedError


class locked_file:
    locked = False

    def __init__(self, filename, mode, block=True, encoding=None):
        if mode not in {'r', 'rb', 'a', 'ab', 'w', 'wb'}:
            raise NotImplementedError(mode)
        self.mode, self.block = mode, block

        writable = any(f in mode for f in 'wax+')
        readable = any(f in mode for f in 'r+')
        flags = functools.reduce(operator.ior, (
            getattr(os, 'O_CLOEXEC', 0),  # UNIX only
            getattr(os, 'O_BINARY', 0),  # Windows only
            getattr(os, 'O_NOINHERIT', 0),  # Windows only
            os.O_CREAT if writable else 0,  # O_TRUNC only after locking
            os.O_APPEND if 'a' in mode else 0,
            os.O_EXCL if 'x' in mode else 0,
            os.O_RDONLY if not writable else os.O_RDWR if readable else os.O_WRONLY,
        ))

        self.f = os.fdopen(os.open(filename, flags, 0o666), mode, encoding=encoding)

    def __enter__(self):
        exclusive = 'r' not in self.mode
        try:
            _lock_file(self.f, exclusive, self.block)
            self.locked = True
        except OSError:
            self.f.close()
            raise
        if 'w' in self.mode:
            try:
                self.f.truncate()
            except OSError as e:
                if e.errno not in (
                    errno.ESPIPE,  # Illegal seek - expected for FIFO
                    errno.EINVAL,  # Invalid argument - expected for /dev/null
                ):
                    raise
        return self

    def unlock(self):
        if not self.locked:
            return
        try:
            _unlock_file(self.f)
        finally:
            self.locked = False

    def __exit__(self, *_):
        try:
            self.unlock()
        finally:
            self.f.close()

    open = __enter__
    close = __exit__

    def __getattr__(self, attr):
        return getattr(self.f, attr)

    def __iter__(self):
        return iter(self.f)
