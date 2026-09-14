"""Run a command under a pseudo-terminal and wait for an expected line.

Thin dev-only helper for the simtest gate phase (Unix-only: the ``pty``
module has no Windows backend; CI runs Ubuntu, devs run macOS).

Why a pty: SimAVR writes UART bytes through stdio, which block-buffers when
piped, so a plain redirect may never show the output before the run is
stopped. Under a pty the stream is line-buffered and every line arrives
promptly on any host. The child is killed as soon as the expected line
matches (or when the timeout expires), and the exit status reports the match.
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time

try:
    import pty
except ImportError:  # Windows has no pty backend.
    print("error: simavr_pty.py needs a Unix host with the pty module", file=sys.stderr)
    raise SystemExit(2)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect", required=True, help="line that proves success")
    parser.add_argument(
        "--timeout", type=float, default=60.0, help="seconds to wait for --expect"
    )
    parser.add_argument("command", nargs="+", help="command to run under the pty")
    return parser.parse_args(argv)


def main(argv) -> int:
    args = parse_args(argv)
    child_pid, fd = pty.fork()
    if child_pid == 0:
        try:
            os.execvp(args.command[0], args.command)
        except OSError as error:
            print(f"error: cannot run {args.command[0]}: {error}", file=sys.stderr)
            os._exit(127)  # noqa: SLOS001 - child side of pty.fork must exit raw.
    tail = b""
    matched = False
    deadline = time.monotonic() + args.timeout
    try:
        while time.monotonic() < deadline and not matched:
            try:
                chunk = os.read(fd, 1024)
            except OSError:
                break
            if not chunk:
                break
            os.write(1, chunk)
            tail = (tail + chunk)[-8192:]
            matched = args.expect.encode() in tail
    finally:
        try:
            os.kill(child_pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(child_pid, 0)
        except ChildProcessError:
            pass
        os.close(fd)
    if not matched:
        print(
            f"error: timed out after {args.timeout:g}s waiting for {args.expect!r}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
