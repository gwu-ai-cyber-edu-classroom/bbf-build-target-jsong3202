# Fix triage

Three valid breaks were filed, with three distinct root causes. All are small,
well-understood, and independently fixable, so we are fixing all three — one PR each.

We are fixing:
1. #1 — P1 IDOR read: `view_note` (`GET /note/<id>`) selects a row by id with only a
   logged-in check and no ownership check, so any authenticated user can read any note
   (incl. the canary). Fix: scope the `SELECT` by `user_id`.
2. #2 — P5 IDOR delete: `delete_note` (`POST /note/<id>/delete`) deletes by id with the
   same missing ownership check, letting any user destroy another's entry. Distinct
   handler and query from #1. Fix: scope the `DELETE` by `user_id`.
3. #3 — P1 auth bypass: `app.secret_key` is the hardcoded value `"journ-dev-secret"`.
   Flask session cookies are signed (not encrypted) with this key, so anyone who knows
   it can forge a valid cookie for any `user_id` — full impersonation, no password.
   Distinct from the IDORs (broken authentication, not missing authorization).
   Fix: load the key from the environment; fall back to a random per-process key.

We are not fixing (yet):
- (none) — all three filed breaks are addressed.

## Why these are three separate fixes, not one
- #1 and #2 are *authorization* gaps in two different handlers/queries; fixing one does
  not fix the other.
- #3 is an *authentication* gap: even with #1/#2 fixed, a forged cookie still
  authenticates as the victim, after which every per-user query happily serves the
  attacker. Closing #3 does not close #1/#2 either (a logged-in user can still walk ids).
