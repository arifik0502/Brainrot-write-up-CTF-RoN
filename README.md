# CTF Return of Nexus — Writeups

Collection of writeups from **CSSCTF**, team **CTF Return of Nexus**. Pwn, blockchain, crypto — vibes immaculate, binaries cooked. 💀

## Challenges

| Category | Challenge | Points | Difficulty | Status | Writeup |
|---|---|---|---|---|---|
| Misc / Warm-up | [Warm-up — Logic Gate Decode](misc/warm-up/README.md) | — | Warm-up | ✅ Solved | [README](misc/warm-up/README.md) |
| Pwn | [Sector 01 — Maintenance Log](pwn/sector-01-maintenance-log/README.md) | 50 | Beginner/Medium | ✅ Solved | [README](pwn/sector-01-maintenance-log/README.md) |
| Blockchain | [The Checkpoint](blockchain/the-checkpoint/README.md) | — | — | ✅ Solved | [README](blockchain/the-checkpoint/README.md) |
| Blockchain | [The Lottery](blockchain/the-lottery/README.md) | — | — | ✅ Solved | [README](blockchain/the-lottery/README.md) |
| Crypto | [Chimera Vault](crypto/chimera-vault/README.md) | 161 | Intermediate | ✅ Solved | [README](crypto/chimera-vault/README.md) |
| Web | [Stars! — Star City Observatory](web/stars-city-observatory/README.md) | — | — | 🟡 In Progress | [README](web/stars-city-observatory/README.md) |
| OSINT | [Server Juice](osint/server-juice/README.md) | 50 | Beginner | 🟡 In Progress | [README](osint/server-juice/README.md) |

## Categories

- **Misc** — logic-gate truth tables disguised as diagrams
- **Pwn** — stack leaks, off-by-one overflows, in-binary ROP, and lazier ret-to-win shortcuts
- **Blockchain** — Solidity `tx.origin` gates, predictable on-chain randomness
- **Crypto** — acoustic FFT demodulation, matrix trace invariants, Merkle-Hellman knapsack
- **Web** — GraphQL schema overexposure / IDOR hunting
- **OSINT** — social-media reconnaissance

## Tools used

`pwntools`-free stdlib Python sockets, `numpy`, `scipy` (Delaunay), `networkx`, static disassembly by hand, Solidity/Foundry for attacker contracts.

## Repo structure

```text
ctf-writeups/
├── README.md
├── misc/
│   └── warm-up/
│       └── README.md
├── pwn/
│   └── sector-01-maintenance-log/
│       ├── README.md
│       ├── exploit.py                 (ROP-chain into admin_check())
│       └── exploit_v2_ret2win.py      (direct ret-to-win, simpler)
├── blockchain/
│   ├── the-checkpoint/
│   │   └── README.md
│   └── the-lottery/
│       ├── README.md
│       └── exploit/
│           └── Attack.sol
├── crypto/
│   └── chimera-vault/
│       ├── README.md
│       └── solve.py
├── web/
│   └── stars-city-observatory/
│       └── README.md                  (in progress)
└── osint/
    └── server-juice/
        └── README.md                  (in progress)
```
