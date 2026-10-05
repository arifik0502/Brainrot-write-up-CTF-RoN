# Server Juice 🧃📱 *(IN PROGRESS)*

> "If you want to appease the algorithm (and maybe get a head start on future hints), consider keeping us on your radar by following." bro named it "Server Juice" to bait us into checking HTTP headers and it's actually just "go follow us on Instagram." certified troll challenge. 💀

## Challenge Information

- Category: OSINT
- Points: 50
- Difficulty: Beginner
- Status: **IN PROGRESS** — platform identified, flag not yet pulled
- Flag format: `CSSCTF{...}`

## TL;DR

Don't get baited by the name. "Server Juice" sounds like an HTTP-headers / server-fingerprinting challenge, but it's filed under **OSINT**, and the flavor text ("appease the algorithm", "keeping us on your radar by following") is pure social-media bait language. A paid "Social" sub-hint points straight at Instagram and Facebook. The flag lives on the organiser's (USyd Cyber Security Society) social account — bio, link-in-bio, or pinned post.

## Analysis

The name is the actual trap here — "Server" screams headers/banners, but there's zero server-side angle in the prompt once you read past the title. "appease the algorithm" + "following" = this is about following a social media account, not probing a server. Classic OSINT misdirection via naming. 🎣

## Method

1. Find the society's handle — check the CTF site footer / about page, or search "Cyber Security Society University of Sydney."
2. Read the **profile bio first** — OSINT flags most often get pasted directly in the bio or the link-in-bio.
3. If not in the bio, check the **pinned post** and the most recent captions on both Instagram and Facebook.
4. Cross-check Facebook's **About/Intro** section too — some orgs stash it there instead of the bio.

## Status

Platform identified (Instagram + Facebook, USyd Cyber Security Society). **Flag not yet captured** — next step is literally just opening the account and reading the bio/pinned post for `CSSCTF{...}`.

## Flag

```text
Not yet obtained — read directly off the society's Instagram/Facebook bio or pinned post once located.
```

## Lessons Learned (so far)

- Challenge *names* in OSINT/misc categories are sometimes deliberately misleading — read the flavor text for the actual mechanism, not the title.
- Paid/unlockable hints that mention a specific medium (here: "Social") are usually the fastest route — don't skip them trying to be clever.
- Bio and pinned-post are the first two places to check on any social-OSINT challenge before digging deeper (comments, older posts, tagged photos).
