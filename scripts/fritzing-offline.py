#!/usr/bin/env python3
"""Exec native Fritzing with Linux seccomp denying network socket creation.

Qt's Unix-domain IPC remains available. No preference, proxy or application code
can re-enable Internet sockets in this process or its children. Fail closed if
libseccomp or kernel support is unavailable. Installer downloads run separately.
"""
import ctypes
import errno
import os
import resource
import socket
import sys


class Comparison(ctypes.Structure):
    _fields_ = [("arg", ctypes.c_uint), ("op", ctypes.c_int),
                ("datum_a", ctypes.c_uint64), ("datum_b", ctypes.c_uint64)]


def deny_network():
    seccomp = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    seccomp.seccomp_init.argtypes = [ctypes.c_uint32]
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_syscall_resolve_name.restype = ctypes.c_int
    seccomp.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(Comparison)]
    seccomp.seccomp_load.argtypes = [ctypes.c_void_p]
    seccomp.seccomp_release.argtypes = [ctypes.c_void_p]
    context = seccomp.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not context:
        raise OSError("Unable to initialize seccomp")
    try:
        deny = 0x00050000 | errno.EPERM  # SCMP_ACT_ERRNO
        # SCMP_CMP_NE=1: only AF_UNIX (Qt local IPC) is permitted.
        argument = Comparison(0, 1, socket.AF_UNIX, 0)
        for name in (b"socket", b"socketpair"):
            syscall = seccomp.seccomp_syscall_resolve_name(name)
            if syscall < 0 or seccomp.seccomp_rule_add_array(context, deny, syscall, 1, ctypes.byref(argument)) < 0:
                raise OSError(f"Cannot install network denial for {name.decode()}")
        # io_uring can create sockets without the socket syscall.
        syscall = seccomp.seccomp_syscall_resolve_name(b"io_uring_setup")
        if syscall >= 0 and seccomp.seccomp_rule_add_array(context, deny, syscall, 0, None) < 0:
            raise OSError("Cannot disable io_uring")
        if seccomp.seccomp_load(context) < 0:
            raise OSError("Kernel rejected the network-denial filter")
    finally:
        seccomp.seccomp_release(context)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: fritzing-offline.py EXECUTABLE [ARGUMENTS...]")
    # Remove inherited network-capable descriptors before loading the filter.
    descriptor_limit = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
    os.closerange(3, descriptor_limit if descriptor_limit != resource.RLIM_INFINITY else 1048576)
    try:
        deny_network()
    except OSError as error:
        raise SystemExit(f"Refusing to run Fritzing without enforced offline mode: {error}")
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
