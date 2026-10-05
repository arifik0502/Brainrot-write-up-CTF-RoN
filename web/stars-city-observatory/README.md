# Stars! — Star City Observatory 🔭🟡 *(IN PROGRESS)*

> "Aligning telescope…" bro the UI is stalling us but the GraphQL endpoint is right there in the Network tab being extremely for-real about it. 👀

## Challenge Information

- Category: Web
- Status: **IN PROGRESS** — attack path mapped, flag not yet captured
- Flag format: `CSSCTF{...}`

## TL;DR

SvelteKit app, creds `cadet` / `star` get you in, the "Stars!" page is a fake-loading placeholder that actually pulls everything from a GraphQL endpoint at `/graphql`. Introspection shows the schema exposes **way more fields than the UI ever renders** — specifically `Person.description` and a bare `user` / `star(id:)` query. Classic GraphQL overexposure: the frontend politely only shows you `name` and `magnitude`, but the backend will happily hand you whatever field you ask it for. The flag is almost certainly sitting in a `description` field nobody bothered to hide from the schema. 🫠

## Recon

Login hint on the page: `cadet` / `star`. After auth, the "Stars!" page shows only a loading placeholder and fetches its real data client-side from `/graphql` (visible in DevTools → Network).

### Schema (recovered via introspection)

```graphql
type Query {
  stars: [Star]
  star(...): Star
  galaxies: [Galaxy]
  galaxy: Galaxy
  user: Person
}

type Star {
  id
  name
  magnitude
  classification
  galaxy: Galaxy
  owner: Person
}

type Person {
  id
  first_name
  last_name
  description
  date_of_birth
}

type Galaxy {
  id
  name
  type
  distanceLy
  stars: [Star]
}
```

The UI list filters down to `name`/`magnitude`/`classification` — the schema exposes `Person.description` and an unfiltered `user`/`star(id:)` query nobody's gating client-side. GraphQL introspection basically hands you the entire menu even when the dining room only shows you three items. 📋

## Next steps (not yet run to completion)

Pull every star's owner, including the `description` field the UI never renders:

```js
fetch('/graphql', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: `{ stars { id name owner { id first_name last_name description } } }`
  })
}).then(r => r.json()).then(d => console.log(d));
```

If the flag isn't sitting in that dump, brute the `star(id:)` resolver directly for IDs the stars list doesn't surface (an admin/hidden record):

```js
for (let i = 1; i <= 12; i++) {
  fetch('/graphql', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: `{ star(id:${i}) { id name owner { first_name description } } }`
    })
  }).then(r => r.json()).then(d => console.log(i, d));
}
```

Both queries reuse the login session cookie, so they run straight out of the DevTools console post-auth — no separate auth header needed.

## Status

Attack path confirmed: GraphQL overexposure via introspection, target is a `Person.description` field. **Flag not yet captured** — next session should run the queries above and grep the response for `CSSCTF{`.

## Flag

```text
Not yet obtained — pending the queries above. Whichever description field contains CSSCTF{...}
is the flag; update this file once captured.
```

## Lessons Learned (so far)

- Never trust the frontend's field selection as an access boundary — if the schema allows a field, assume it's reachable regardless of what the UI happens to render.
- GraphQL introspection being left enabled on a production-ish endpoint is itself most of the vulnerability — it hands an attacker the full data model for free.
- A bare `user`/`star(id:)` query with no visible auth/ownership check is an IDOR waiting to happen; always sweep adjacent IDs once you spot one.
