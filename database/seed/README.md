# Synthetic data

Put the synthetic datasets here (Chapter 4, section 4.11):

- `S1` – ten tasks with hand-computed expected results.
- `S2` – about 5,000 records for the NFR-05 performance test.

No real project data without a recorded consent reference (NFR-01).

## Files

| File | Content |
|---|---|
| `S1.sql` | Project `PRJ-S1`: 10 tasks, 8 FS dependencies, 11 snapshots, 4 resources, 3 draft scenarios (SC1–SC3) and 3 treatment options |
| `S1_expected.md` | Hand-computed expected results for each test case at `as_of = 2026-03-16`, plus the open design points D1–D7 |
| `S2.sql` | Project `PRJ-S2`: 1,000 tasks × 5 snapshots = **5,000 `task_snapshots` records**, 900 FS dependencies; deterministic (no `random()`) |

Both files are fully synthetic (`data_mode = 'synthetic'`) and use pseudonymous codes only.
The test password of every seeded user is given in `S1_expected.md` (only its bcrypt hash is stored).

## Loading

Run after `database/Schema_Script.sql`, on an empty schema (each file runs in one transaction):

```powershell
psql -U mahwar -d mahwar -v ON_ERROR_STOP=1 -f database/seed/S1.sql
psql -U mahwar -d mahwar -v ON_ERROR_STOP=1 -f database/seed/S2.sql
```

The files are not re-runnable (unique codes). To reload, recreate the database as `postgres`:

```sql
DROP DATABASE mahwar;
CREATE DATABASE mahwar OWNER mahwar;
```

then run `Schema_Script.sql`, `S1.sql` and `S2.sql` again.
