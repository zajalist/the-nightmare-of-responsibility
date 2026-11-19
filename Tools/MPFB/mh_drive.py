"""Send MakeHuman script code to the live app (plugin 9_foa_driver on 127.0.0.1:12346) and print the result.
  python Tools/MPFB/mh_drive.py "print(human.getAge())"
  python Tools/MPFB/mh_drive.py @file.py"""
import json
import socket
import sys

TOKEN = open("C:/Users/Admin/.foa/mh_driver_token").read().strip()


def run(code, timeout=150):
    with socket.create_connection(("127.0.0.1", 12346), timeout=timeout) as s:
        s.sendall((json.dumps({"token": TOKEN, "code": code}) + "\n").encode("utf-8"))
        buf = b""
        while not buf.endswith(b"\n"):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    return json.loads(buf.decode("utf-8"))


if __name__ == "__main__":
    arg = sys.argv[1]
    code = open(arg[1:], encoding="utf-8").read() if arg.startswith("@") else arg
    r = run(code)
    print(r.get("out", ""), end="")
    if not r.get("ok"):
        print(r.get("error", ""), file=sys.stderr)
        sys.exit(1)
