# Buffer hash goldens (Tier 2)

After a script runs under `PIXIL_TEST_MODE=1`, Pixil records a **fingerprint** of
non-transparent pixels in the LED drawing buffer (16 hex chars, or the word
`empty` if nothing was drawn). These `.hash` files are **not** images.

Parent docs: [tests/scripts/README.md](../README.md), [tests/README.md](../../README.md), [Pixil_Development_Guide.txt §8](../../../docs/Pixil_Development_Guide.txt).

## First capture for a new manifest script (on Pi, matrix attached)

```bash
./run test-scripts
```

**Default behavior:** compares existing goldens and **creates** `golden/<name>.hash`
only for non-volatile scripts that do not have a file yet (`golden created -> ...`).
Existing goldens are not overwritten.

Example: `testing/test_math.pix` → `test_math.hash`

## Compare (normal runs)

```bash
./run test-scripts
# or
./run test-all
```

Output includes `golden ok (...)`, `golden created -> ...`, or `buffer hash mismatch`.

## Refresh after intentional visual change (overwrite all)

```bash
PIXIL_TEST_UPDATE_GOLDEN=1 ./run test-scripts
# or
./run test-scripts -- --update-golden
```

Overwrites every non-volatile golden. Commit only the `.hash` files you meant to change.

## Compare only (no auto-create for missing)

```bash
./run test-scripts -- --no-update-missing
# or
PIXIL_TEST_UPDATE_MISSING_GOLDEN=0 ./run test-scripts
```

## Volatile scripts (no golden)

Scripts that draw **live clock** or **`get_system("runtime")`** cannot have stable
hashes. Mark them in `manifest/core.txt`:

```
testing/test_datetime.pix volatile
testing/test_system.pix volatile
```

Do **not** store or commit `.hash` files for those scripts. `PIXIL_TEST_UPDATE_GOLDEN=1` removes stale volatile goldens if present.

## Commit checklist

- [ ] One `.hash` per non-volatile entry in `core.txt`
- [ ] No `test_datetime.hash` or `test_system.hash` (volatile)
- [ ] `manifest/core.txt` updated if you added/removed scripts
