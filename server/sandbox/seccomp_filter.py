"""Minimal, dependency-free seccomp-BPF syscall filter (stdlib ctypes only).

Installs a *denylist* filter that makes a language-level sandbox escape harmless:
even if user code reaches ``os``/``socket``/``subprocess``, the kernel refuses the
syscalls needed to talk to the network or spawn a process. File reads are left
allowed on purpose — the bot token is already unreachable (root-only /secrets +
uid drop), and everything else readable is non-secret, so a bypass is reduced to
pure computation over public files.

Denylist (not allowlist) so normal interpreter operation is never broken: we only
forbid a handful of syscalls and return EPERM (a catchable OSError) for them.

Call install() once, right before running untrusted code. It is a no-op (returns
False) on unsupported architectures or if the kernel rejects the filter, so the
caller can decide how strict to be about that.
"""
import ctypes
import ctypes.util
import platform
import struct

# prctl / seccomp constants
PR_SET_NO_NEW_PRIVS = 38
PR_SET_SECCOMP = 22
SECCOMP_MODE_FILTER = 2

# BPF return actions
SECCOMP_RET_KILL_PROCESS = 0x80000000
SECCOMP_RET_ERRNO = 0x00050000
SECCOMP_RET_ALLOW = 0x7FFF0000
EPERM = 1

# audit arch tokens (must match the running arch, else the filter KILLs)
AUDIT_ARCH_X86_64 = 0xC000003E
AUDIT_ARCH_AARCH64 = 0xC00000B7

# offsets into struct seccomp_data
_OFF_NR = 0
_OFF_ARCH = 4

# BPF instruction opcodes
BPF_LD = 0x00
BPF_W = 0x00
BPF_ABS = 0x20
BPF_JMP = 0x05
BPF_JEQ = 0x10
BPF_K = 0x00
BPF_RET = 0x06

# Syscalls to forbid, per arch: network (socket/connect) + process spawn
# (execve/execveat/fork/vfork/clone/clone3) + ptrace. Blocking `socket` alone
# stops all networking (no socket fd can be created); the rest close exec/fork.
_DENY = {
    'x86_64': {
        'arch': AUDIT_ARCH_X86_64,
        'nrs': [41, 42, 44, 46, 59, 322, 57, 58, 56, 435, 101],
        # socket, connect, sendto, sendmsg, execve, execveat, fork, vfork,
        # clone, clone3, ptrace
    },
    'aarch64': {
        'arch': AUDIT_ARCH_AARCH64,
        'nrs': [198, 203, 206, 211, 221, 281, 220, 435, 117],
        # socket, connect, sendto, sendmsg, execve, execveat, clone, clone3, ptrace
    },
}


def supported():
    """True if this architecture has a denylist we know how to install."""
    return platform.machine() in _DENY


def _sock_filter(code, jt, jf, k):
    # struct sock_filter { __u16 code; __u8 jt; __u8 jf; __u32 k; }
    return struct.pack('HBBI', code, jt, jf, k)


def _build_program(arch_token, nrs):
    prog = []
    # Load arch; kill if it is not the one we built for (blocks x32/ABI confusion).
    prog.append(_sock_filter(BPF_LD | BPF_W | BPF_ABS, 0, 0, _OFF_ARCH))
    prog.append(_sock_filter(BPF_JMP | BPF_JEQ | BPF_K, 1, 0, arch_token))
    prog.append(_sock_filter(BPF_RET | BPF_K, 0, 0, SECCOMP_RET_KILL_PROCESS))
    # Load syscall number, then compare against each denied nr. On a match, jump
    # forward *past* the ALLOW terminator to the EPERM terminator; on a miss, fall
    # through to the next comparison (and, after the last one, to ALLOW). ALLOW
    # must precede EPERM so that a non-matching syscall is permitted, not denied.
    prog.append(_sock_filter(BPF_LD | BPF_W | BPF_ABS, 0, 0, _OFF_NR))
    n = len(nrs)
    for i, nr in enumerate(nrs):
        prog.append(_sock_filter(BPF_JMP | BPF_JEQ | BPF_K, n - i, 0, nr))
    prog.append(_sock_filter(BPF_RET | BPF_K, 0, 0, SECCOMP_RET_ALLOW))
    prog.append(_sock_filter(BPF_RET | BPF_K, 0, 0, SECCOMP_RET_ERRNO | EPERM))
    return b''.join(prog), len(prog)


def install():
    """Install the seccomp filter. Returns True on success, False if unavailable."""
    spec = _DENY.get(platform.machine())
    if spec is None:
        return False
    try:
        libc = ctypes.CDLL(ctypes.util.find_library('c') or 'libc.so.6', use_errno=True)
    except OSError:
        return False

    # Explicit signature: prctl(int, unsigned long, unsigned long, ...). Without
    # this, ctypes truncates the 64-bit struct pointer and the kernel installs a
    # garbage filter -> crash. c_ulong holds a pointer on LP64.
    libc.prctl.restype = ctypes.c_int
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                           ctypes.c_ulong, ctypes.c_ulong]

    blob, count = _build_program(spec['arch'], spec['nrs'])
    buf = ctypes.create_string_buffer(blob, len(blob))

    # struct sock_fprog { unsigned short len; struct sock_filter *filter; }
    class SockFprog(ctypes.Structure):
        _fields_ = [('len', ctypes.c_ushort),
                    ('filter', ctypes.c_void_p)]

    fprog = SockFprog(count, ctypes.cast(buf, ctypes.c_void_p))

    # No new privileges is a precondition for an unprivileged filter install.
    if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        return False
    fprog_addr = ctypes.cast(ctypes.byref(fprog), ctypes.c_void_p).value
    if libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, fprog_addr, 0, 0) != 0:
        return False
    return True
