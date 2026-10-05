# Chimera Vault 🔐🎵

> The ancient custodians of the Chimera Vault didn't rely on standard asymmetric primitives to secure their root register. Demodulate the carrier, trace the invariant through the matrix state transitions, and invert the resonance to breach the vault.

bro really gated a flag behind three entire crypto subfields in one challenge. certified multi-stage moment. 💀

## Challenge Information

- Category: Cryptography (with an acoustic / signal-processing front door)
- Points: 161
- Difficulty: Intermediate
- Target: `nc 34.116.80.78 7334`
- Files: `chimera_vault_tar.gz` (`server.py`, `Dockerfile`)
- Flag format: `CSSCTF{...}`

## TL;DR

The server gates the flag behind three stages:

1. **Decode a session token** from a two-tone audio burst, via FFT.
2. **Notice the matrix "drift" leaks the secret multiplier `W`** as the trace of the difference of two consecutive matrices.
3. **Use `W` to strip the modular mask** off a Merkle–Hellman knapsack, turning it back into a super-increasing one a greedy algorithm solves exactly.

The flavor text is literally a table of contents:

| Hint in the text | What it maps to |
|---|---|
| "Demodulate the carrier" | Phase 1: recover the session token from the audio via FFT |
| "Trace the invariant through the matrix state transitions" | Phase 2: `trace(M_{k+1} - M_k) = W` is constant |
| "Invert the resonance" | Phase 3: undo the modular multiplication, then solve the knapsack |

## Files

The archive contained the full `server.py` — white-box challenge. It runs behind `socat` with a 45-second timeout (`signal.alarm(45)` inside the script too), so the solver has to be fully automated.

Per connection, the server generates fresh random state and walks the player through:

| Phase | Server prints | Server expects |
|---|---|---|
| 0 | Modulus `N` (128-bit RSA-style), knapsack modulus `M_mod` | — |
| 1 | Base64 of 8 kHz mono 16-bit PCM audio | Session token in hex |
| 2 | Matrices `M_0 ... M_3` (3x3 over `Z_N`) | — |
| 3 | 48 knapsack weights `S` and a target sum | 48-bit binary solution string |

Quirk: `__init__` generates `W`, `D`, and `M` once, then throws them away and regenerates after the knapsack parameters are chosen (so `W` ends up coprime to `M_mod`). Only the second `W` matters, and it's the one baked into the knapsack.

## Tools

Python 3, `numpy`, stdlib `socket` — no `pwntools` dependency.

## Solution

### Phase 1 — demodulating the carrier

The audio is two sine waves plus light Gaussian noise:

```text
f1 = 440 + (token & 0xFF) * 5
f2 = 1200 + ((token >> 8) & 0xFF) * 5
sample = 0.4*sin(2*pi*f1*t) + 0.4*sin(2*pi*f2*t) + N(0, 0.05)
```

So the token is just two bytes encoded as two frequencies, 5 Hz steps apart. Token range is `[0x1000, 0xEFFF]`, so the high byte is always `0x10–0xEF`.

**Why FFT works cleanly:** the burst is 0.8 s at 8000 Hz → `N = 6400` samples, bin width `8000/6400 = 1.25 Hz`. Both tones are multiples of 5 Hz, so each completes a whole number of cycles in the window — no spectral leakage with a rectangular window. Each tone lands exactly on FFT bin `f * 4/5`.

**The ambiguity:** `f1` spans 440–1715 Hz, `f2` spans 1280–2385 Hz — they overlap in 1280–1715 Hz. If both peaks fall in that shared band, swapping `f1`/`f2` gives an indistinguishable signal (equal amplitude, zero phase). Affects roughly 10% of connections. Also: if `f1 == f2`, the single bin has double amplitude (`2A`) instead of two separate peaks — scoring by residual against the *expected* amplitude (not raw peak height) avoids misreading that as two tones.

Instead of naive peak-picking (which can lock onto the wrong tone when both fall in the overlap band), the solver scores **every** candidate token (~52,000) against the spectrum in one vectorized numpy expression:

```python
A = 0.4 * 32767 * n / 2
res = where(i1 == i2, |spec[i1] - 2A|, |spec[i1] - A| + |spec[i2] - A|)
candidates = tokens where res < res.min() + 0.05*A
```

On the real instance this decoded to `0x4729`: low byte `0x29` (41) → `f1 = 645 Hz`, high byte `0x47` (71) → `f2 = 1555 Hz`. 645 Hz is outside the overlap band, so this run was unambiguous and the server accepted it immediately.

### Phase 2 — tracing the invariant

After the token is accepted, the server prints `M_0` then three evolved matrices:

```text
M_{k+1} = M_k + D (mod N)
D = diag(d1, d2, d3), d3 = (W - d1 - d2) mod N
```

Despite the "non-commutative matrix drift" flavor text, the rule is just repeated addition of a fixed diagonal matrix — nothing non-commutative actually happens. The matrices themselves are decoration; what matters is the trace:

```text
trace(M1) - trace(M0) = trace(D) = d1 + d2 + d3 ≡ W (mod N)
```

Since `W` is drawn from `[2, N-2]`, it's already fully reduced — no search needed, `W` falls out exactly:

```python
W = (tr(M1) - tr(M0)) % N
```

The individual diagonal entries `d1`, `d2` are never needed — the trace alone is enough. Any two consecutive matrices give the same answer; the solver uses `M_0` and `M_1`.

### Phase 3 — inverting the resonance

The knapsack is a textbook Merkle–Hellman construction:

```text
r      : super-increasing sequence, r_i > sum(r_0 ... r_{i-1}), 48 elements
M_mod  : modulus with M_mod > sum(r), odd
W      : multiplier with gcd(W, M_mod) = 1
S_i    = (W * r_i) mod M_mod       <- public weights
target = sum(b_i * S_i)            <- b = secret 48-bit vector, sum NOT reduced
```

The hard problem is subset-sum on `S`, which looks random. The trapdoor is `W` — and Phase 2 just handed it over.

| Step | Why it's valid |
|---|---|
| `Winv = W^-1 mod M_mod` | `W` is coprime to `M_mod` by construction (server loops until `gcd == 1`) |
| `r_i = S_i * Winv mod M_mod` | `S_i = W*r_i mod M_mod` and `r_i < M_mod`, so the reduction recovers `r_i` exactly |
| `t = target * Winv mod M_mod` | `target = sum b_i S_i ≡ W * sum b_i r_i`, so `t ≡ sum b_i r_i`. Since `sum(r) < M_mod`, the residue is the true integer sum |
| Greedy largest→smallest: if `r_i <= t`, set `b_i = 1`, subtract | Super-increasing weights force a unique greedy solution |

Uniqueness matters because the server checks `user_bits == target_bits`, not just that the weighted sum matches. Super-increasing weights guarantee only one subset hits the target, so there's no risk of submitting a different-but-valid one. The solver asserts the remainder is `0` after the greedy pass as a sanity check.

```python
def solve_knapsack(S, target_sum, W, M_mod):
    W_inv = pow(W, -1, M_mod)
    r = [(W_inv * s) % M_mod for s in S]
    remaining = (W_inv * target_sum) % M_mod
    bits = [0] * len(S)
    for i in range(len(r) - 1, -1, -1):  # largest to smallest
        if r[i] <= remaining:
            bits[i] = 1
            remaining -= r[i]
    assert remaining == 0
    return ''.join(str(b) for b in bits)
```

## Debugging / Failed Attempts

The sandbox used to develop the solver had no outbound network access, so it was first validated against a local copy of `server.py` served over TCP. Two bugs surfaced:

| Bug found | Fix |
|---|---|
| Peak-picking merged two tones within ~15 Hz of each other, giving a wrong token (1 failure in 12 runs) | Replaced with exhaustive scoring over all tokens on an unwindowed FFT |
| Candidates with `f1 == f2` tied with the real pair because the same bin was counted twice | Score by residual against expected amplitude (`A` for a lone tone, `2A` for merged tones) |
| FFT bin index computed as `4*f` instead of `f*N/rate = 0.8*f` → `IndexError` | Use `f*4//5` |

Final version solved 30/30 local runs, including ones needing a reconnect for the swap ambiguity.

## Final Exploit / Solver

```python
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
```

Also saved as [`solve.py`](solve.py).

## Running the Exploit

```bash
python3 solve.py
```

## Result

```text
PS C:\Users\SHAMI\Downloads> py solve.py
token candidates: ['0x4729']
solution: 010101101001011000011011000000001101010001001100
   vector (binary string e.g. 10101...):
[+] RESONANCE EQUILIBRIUM ACHIEVED. OVERWRITING MASTER KEY...
[+] Flag: CSSCTF{tr4c3_1nv4r14nc3_4nd_4c0ust1c_sp3ctr4_7f9b8c}
```

(The ` vector (binary string...` line is just the tail of the server's own prompt text being echoed back — harmless.)

## Flag

```text
CSSCTF{tr4c3_1nv4r14nc3_4nd_4c0ust1c_sp3ctr4_7f9b8c}
```

## Lessons Learned

| Weakness | Explanation |
|---|---|
| Secret leaked through a "public" invariant | The matrix stage exists only to publish `tr(D) = W`. Any value that's a linear function of a secret, and observable in the clear, *is* the secret. |
| Merkle–Hellman is broken by design | The 1980s knapsack scheme is known to fall to Shamir's attack and lattice-based attacks generally. Density here (~48 elements over ~52-bit weights, ≈0.9) is borderline for plain LLL, so the matrix leak is the clean, deterministic route. |
| Token entropy is tiny | The "carrier" encodes only 16 bits, and a reconnect costs nothing — friction, not security. |
| Server state isn't bound to the session | Every connection is independent, so ambiguous cases can be retried freely. |

**Alternative route (noted, not needed):** if `W` hadn't leaked, the standard approach is building the lattice for the low-density subset-sum problem (Lagarias–Odlyzko / CJLOSS embedding) from the 48 weights and target, then running LLL/BKZ for the short vector. Worth keeping in the toolbox for similar challenges without the convenient trace leak.

**Generalizable checklist:**

1. Read the challenge text as a spec — each sentence usually names one stage.
2. When source is given, look for quantities constant across steps (invariants) — they're usually the leak.
3. For signal stages, check whether tones align to FFT bins; if so, rectangular window + exact bin lookup.
4. For remote challenges with short timeouts, automate from the start and build in retry for probabilistic failures.
5. Test against a local copy of the provided server before touching the real one.
