# Warm-up — Logic Gate Decode 🟢⚪

> a diagram of filled (●) and hollow (■) circles, a legend, three rows of eight boxes. "no spaces." bro this was free real estate. 🗿

## Challenge Information

- Category: Misc / Warm-up
- Difficulty: Warm-up (certified baby's-first-chall)
- Flag format: `CSSCTF{...}`

## TL;DR

Legend is just a truth table in disguise. ●=1, ■=0, and the only gate that fits the given legend is **AND** — output only lit when both inputs are lit. 8 boxes per row = 1 byte. Decode 3 rows, get 3 ASCII chars, get the flag. that's it. that's the whole challenge. 💀

## Solution

the legend, decoded as a truth table:

```text
INPUT   OUTPUT
1 1  ->  1        this is an AND gate fr fr:
1 0  ->  0        output is lit ONLY when
0 1  ->  0        BOTH inputs are lit.
0 0  ->  0
```

bro gave us a whole diagram just to say "AND gate" and we respect the bit. 🫡

each box of two circles → one bit via AND. eight boxes per row → one byte → one ASCII char. three rows, three chars:

```text
Row 1: 01100011 = 0x63 = 'c'
Row 2: 01110011 = 0x73 = 's'
Row 3: 01110011 = 0x73 = 's'
```

`c` `s` `s` → the flag was always going to be CSS. the warm-up flag was quite literally announcing the CTF's own name. certified wholesome moment. 🥹

## Flag

```text
CSSCTF{css}
```

## Lessons Learned

nothing to patch here, it's the warm-up — but the general move is: whenever a challenge hands you a "legend" with only two symbol states and a combine rule, it's a truth table wearing a costume. map it to bits, read the bits as bytes, done.
