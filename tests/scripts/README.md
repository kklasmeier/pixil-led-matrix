# Tier 2: Pixil script smoke tests

Runs curated `.pix` files from `manifest/core.txt` through `Pixil.py` on real hardware.

**See also:** [tests/README.md](../README.md) (both tiers), [golden/README.md](golden/README.md) (hash files), [Pixil_Development_Guide.txt §8](../../docs/Pixil_Development_Guide.txt).

## Requirements

- Raspberry Pi with matrix working (`sudo python3 Pixil.py testing/test_print` works)
- **Passwordless sudo** for your user (`sudo -n true` must succeed)
- Tier 1 tests passing (`./run test`)

## Run

```bash
./run test-scripts
# or both tiers:
./run test-all
```

Tests run with `PIXIL_TEST_MODE=1` automatically (via `sudo env ...`):

- **Tier 2 needs sudo** for LED matrix access; `./run test` (Tier 1) does not
- Buffer fingerprints use an IPC queue; optional state file goes under `/tmp/pixil-test-state-<uid>/` (not the repo) so root/pi permission mismatches on mounted trees are avoided
- Caps `rest()` duration (default 0.01s) so suites finish quickly
- Prints `PIXIL_TEST_SUMMARY` (commands, rest count, self-reported fails, buffer hash)
- Optional golden buffer hashes in `golden/` (see `golden/README.md`)

## Skip (CI / dev machine without matrix)

```bash
PIXIL_SKIP_SCRIPT_TESTS=1 ./run test-scripts   # exits 0 with SKIP message
```

## What counts as failure

- Non-zero exit from `Pixil.py`
- `FAIL` anywhere in stdout/stderr (PASS/FAIL scripts)
- Python traceback in output
- Subprocess timeout (default 120s per script)

## Tuning

| Env var | Default | Meaning |
|---------|---------|---------|
| `PIXIL_SCRIPT_TIME_LIMIT` | `1:00` | Passed to Pixil `-t` |
| `PIXIL_SCRIPT_TIMEOUT` | `120` | Wall-clock kill per script |
| `PIXIL_SKIP_SCRIPT_TESTS` | unset | Skip Tier 2 entirely |
| `PIXIL_TEST_REST_CAP` | `0.01` | Max `rest()` seconds in test mode |
| `PIXIL_TEST_UPDATE_GOLDEN` | unset | Set `1` to write `golden/*.hash` files |

## How it works (maintainers)

1. Harness runs `sudo env PIXIL_TEST_MODE=1 python3 Pixil.py <script> -t … -d DEBUG_OFF`
2. Pixil queues drawing commands; the **consumer process** owns the matrix buffer
3. At script end, `__test_snapshot__` runs in the consumer → fingerprint + IPC reply
4. Main process prints `PIXIL_TEST_SUMMARY … buffer=HASH …`
5. Harness parses output; compares `HASH` to `golden/<name>.hash` unless `volatile`

Fingerprint = SHA-256 prefix of non-transparent pixels, or `empty`.

Implementation touchpoints:

| Component | File |
|-----------|------|
| Harness | `run_script_tests.py` |
| Test metrics / summary | `pixil_utils/test_hooks.py` |
| Buffer hash | `rgb_matrix_lib/test_inspect.py` |
| Snapshot command | `shared/command_queue.py`, `Pixil.py` |

## Adding or updating a manifest script

1. Write or edit `scripts/testing/your_test.pix` (short; use `sync_queue` after draws).
2. Add to `manifest/core.txt`:
   ```
   testing/your_test.pix
   ```
   For live clock/runtime text on the matrix:
   ```
   testing/your_test.pix volatile
   ```
3. On the Pi:
   ```bash
   ./run test-scripts                    # should pass (no golden yet, or volatile)
   PIXIL_TEST_UPDATE_GOLDEN=1 ./run test-scripts   # skip step for volatile
   ```
4. Commit `golden/your_test.hash` if not volatile.

Keep `core.txt` small (daily `./run test-all` time). Longer experiments can stay in `scripts/testing/` unlisted until promoted.

## Golden workflow summary

| Goal | Command |
|------|---------|
| First capture | `PIXIL_TEST_UPDATE_GOLDEN=1 ./run test-scripts` |
| Daily verify | `./run test-all` |
| Intentional visual change | Re-run update golden for that script |

See [golden/README.md](golden/README.md) for commit checklist (8 goldens, no volatile files).
