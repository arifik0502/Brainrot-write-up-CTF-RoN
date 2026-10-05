# The Checkpoint (`Gate.sol`) 💀🚪

> bro really made a three-door security gauntlet like this was some skibidi escape room and thought nobody was gonna simply walk through it. spoiler: we walked through it.

## Challenge Information

- Category: Blockchain / Solidity
- Difficulty: Beginner
- Target: `Gate.sol` (source not included in this repo — see note below)
- Files: *none provided in source material* — contract behavior reconstructed from the writeup only

> **Note:** No `Gate.sol` source file was present in the provided material, only a prose description of its behavior. This writeup therefore has no `src/` or exploit contract checked in — only the documented reasoning. If the original `.sol` turns up, drop it in `src/` and wire `exploit/Attack.sol` to it.

## TL;DR

Three gates, three jokes:

1. `tx.origin != msg.sender` check — bypassed by calling through an attacker contract instead of an EOA.
2. "Send ETH" check — just send ETH, `receive()` flips `funded = true`.
3. Password check — the plaintext password was sitting in the contract source, hashed with `keccak256` like that makes it secret.

## Solution

### Door 1 — `enter()`

The gate's first check is:

```solidity
msg.sender != tx.origin
```

Read literally: "only let a **contract** call me, surely nobody can deploy a contract." 💀

For a normal wallet call, `msg.sender == tx.origin` (both are your EOA), so a direct call reverts. Deploy a tiny attacker contract and call `enter()` *from* it instead:

- `msg.sender` = attacker contract
- `tx.origin` = your wallet
- they differ → check passes

Certified contract moment. 🤝

### Door 2 — fund it

Door 2 is just "please send me some ETH." The contract's `receive()` function sets:

```solidity
funded = true;
```

So: send ETH directly to the contract. No exploit, no galaxy brain, just an ETH transfer.

### Door 3 — `claim(bytes32 _password)`

The contract checks the supplied password against:

```solidity
keccak256("gateway to the flag")
```

The password string itself was visible directly in the contract source. Hashing it doesn't make it secret if the preimage is sitting right there in cleartext.

Computed locally:

```text
0x90cd83d7...
```

(truncated in the source writeup — recompute as `keccak256("gateway to the flag")` from the actual contract if reproducing).

Submitted via `claim(0x90cd83d7...)` → door opens.

### Finishing up

```text
enter()      ✅
funded       ✅
claim()      ✅
isSolved()   true
```

Went back to the `netcat` service, submitted the team ticket, got the flag.

## Flag

```text
Retrieved via the netcat ticket flow after isSolved() == true. Exact flag value not recorded
in the source writeup for this specific challenge.
```

## Lessons Learned

| Weakness | Fix |
|---|---|
| `tx.origin` used for access control | Never use `tx.origin` for auth — it breaks the moment any call goes through a contract. Use `msg.sender`. |
| Secret password hardcoded in source | Don't ship secrets in source code, hashed or not — if the preimage is in the bytecode/source, it's public. |

`tx.origin` checks are not security, they're a speed bump with a fancy name. And if your "secret password" is sitting inside the contract source, that's not a secret, that's a public announcement. 📢
