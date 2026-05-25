# Buffer hash goldens (Tier 2)

After a script runs under `PIXIL_TEST_MODE=1`, Pixil records a **fingerprint** of
non-transparent pixels in the LED drawing buffer (16 hex chars, or the word
`empty` if nothing was drawn). These `.hash` files are **not** images.

Parent docs: [tests/scripts/README.md](../README.md), [tests/README.md](../../README.md), [Pixil_Development_Guide.txt §8](../../../docs/Pixil_Development_Guide.txt).

## Capture (on Pi, matrix attached)

```bash
PIXIL_TEST_UPDATE_GOLDEN=1 ./run test-scripts
```

Creates or overwrites `tests/scripts/golden/<script_basename>.hash` for each
**non-volatile** entry in `manifest/core.txt`.

Example: `testing/test_math.pix` → `test_math.hash`

## Compare (normal runs)

```bash
./run test-scripts
# or
./run test-all
```

Output includes `golden ok (...)` or `buffer hash mismatch`.

## Refresh after intentional visual change

```bash
PIXIL_TEST_UPDATE_GOLDEN=1 ./run test-scripts
```

Commit only the `.hash` files you meant to change.

## Volatile scripts (no golden)

Scripts that draw **live clock** or **`get_system("runtime")`** cannot have stable
hashes. Mark them in `manifest/core.txt`:

```
testing/test_datetime.pix volatile
testing/test_system.pix volatile
```

Do **not** store or commit `.hash` files for those scripts. `PIXIL_TEST_UPDATE_GOLDEN=1` removes stale volatile goldens if present.

## Commit checklist

- [ ] 8 golden files for current `core.txt` deterministic scripts
- [ ] No `test_datetime.hash` or `test_system.hash` (volatile)
- [ ] `manifest/core.txt` updated if you added/removed scripts
