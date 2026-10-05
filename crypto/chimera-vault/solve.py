#!/usr/bin/env python3
import socket, sys, re, base64, struct, itertools
import numpy as np

HOST, PORT = "34.116.80.78", 7334
RATE = 8000

def candidates(b64):
    raw = base64.b64decode(b64)
    x = np.array(struct.unpack("<%dh" % (len(raw)//2), raw), dtype=float)
    n = len(x)
    spec = np.abs(np.fft.rfft(x))  # tones fall exactly on bins (1.25 Hz/bin)
    A = 0.4 * 32767 * n / 2        # expected magnitude of one tone
    toks = np.arange(0x1000, 0xF000)
    f1 = 440 + (toks & 0xFF)*5; f2 = 1200 + (toks >> 8)*5
    i1 = f1*4//5; i2 = f2*4//5
    same = (i1 == i2)
    res = np.where(same, abs(spec[i1] - 2*A), abs(spec[i1] - A) + abs(spec[i2] - A))
    best = res.min()
    return [int(t) for t in toks[res < best + 0.05*A]][:4]

def solve_phase3(N, Mmod, M0, M1, S, target):
    W = (M1[0][0]+M1[1][1]+M1[2][2] - (M0[0][0]+M0[1][1]+M0[2][2])) % N
    Winv = pow(W, -1, Mmod)
    r = [(s*Winv) % Mmod for s in S]
    t = (target*Winv) % Mmod
    bits = [0]*len(r)
    for i in reversed(range(len(r))):
        if r[i] <= t:
            bits[i] = 1; t -= r[i]
    assert t == 0, "greedy failed"
    return "".join(map(str, bits))

def parse_mat(line):
    rows = re.findall(r"\[([\d, ]+)\]", line)
    return [[int(v) for v in row.split(",")] for row in rows]

def attempt(host, port):
    import random
    s = socket.create_connection((host, port), timeout=40)
    f = s.makefile("rw", buffering=1)

    def readuntil(marker):
        buf = ""
        while marker not in buf:
            c = f.read(1)
            if not c: break
            buf += c
        return buf

    hdr = readuntil("Enter decoded session token")
    N = int(re.search(r"N = (\d+)", hdr).group(1))
    Mmod = int(re.search(r"M_mod = (\d+)", hdr).group(1))
    b64 = re.search(r"\(Base64\):\s*([A-Za-z0-9+/=]+)", hdr).group(1)
    cands = candidates(b64)
    print("token candidates:", [hex(c) for c in cands])
    if not cands: return None
    if len(cands) > 1: print("ambiguous (overlapping band) - guessing, rerun if rejected")
    readuntil(": ")
    f.write(hex(random.choice(cands)) + "\n"); f.flush()

    rest = ""
    while "Enter 48-bit solution" not in rest:
        c = f.read(1)
        if not c: print("rejected, retrying"); return None
        rest += c

    mats = {int(k): parse_mat(v) for k, v in re.findall(r"M_(\d) = (.*)", rest)}
    S = eval(re.search(r"Weights S = (\[.*?\])", rest).group(1))
    target = int(re.search(r"Resonance Sum\s*=\s*(\d+)", rest).group(1))
    sol = solve_phase3(N, Mmod, mats[0], mats[1], S, target)
    print("solution:", sol)
    f.write(sol + "\n"); f.flush()

    out = f.read(); print(out)
    return out if "CSSCTF" in out or "Flag" in out else None

def main():
    host, port = (sys.argv[1], int(sys.argv[2])) if len(sys.argv) > 2 else (HOST, PORT)
    for i in range(15):
        if attempt(host, port): break

if __name__ == "__main__":
    main()
