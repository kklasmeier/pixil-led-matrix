# Pixil automated tests

Tests are **separate** from normal `Pixil.py` / lightshow runs. `pixil_utils` test
hooks are no-ops unless `PIXIL_TEST_MODE=1` (only set by the Tier 2 harness).

**Also read:** [Pixil_Development_Guide.txt §8](../docs/Pixil_Development_Guide.txt) (overview for developers).

## Layout

```
tests/
├── README.md                 # This file
├── conftest.py               # Shared pytest config and markers
├── pixil/                    # Tier 1: pytest (pixil_utils)
│   ├── COVERAGE.md           # Module ↔ test file map
│   └── test_*.py
├── scripts/                  # Tier 2: .pix harness (Pi + matrix)
│   ├── README.md             # Tier 2 detail (goldens, manifest, env vars)
│   ├── run_script_tests.py   # Harness invoked by ./run test-scripts
│   ├── manifest/core.txt     # Scripts to run (one path per line)
│   └── golden/*.hash         # Optional buffer fingerprints (not images)
└── rgb_matrix/               # Tier 3: reserved (simulated matrix; future)
```

| Tier | Command | Hardware | What it proves |
|------|---------|----------|----------------|
| 1 | `./run test` | None | Math, JIT, conditions, params, parsing |
| 2 | `./run test-scripts` | Pi + matrix + sudo | Scripts run; buffer smoke; golden compare |
| both | `./run test-all` | Tier 1 then Tier 2 | Default check on the Pi before committing |

## Quick start (Raspberry Pi)

```bash
./run setup-tests    # once: sudo apt install python3-pytest
./run test-all       # Tier 1 + Tier 2
```

Tier 1 does **not** need sudo or `rgbmatrix`. Tier 2 uses `sudo -n` (passwordless sudo).

Skip Tier 2 on a machine without a matrix:

```bash
PIXIL_SKIP_SCRIPT_TESTS=1 ./run test
```

## Tier 1: unit tests

```bash
./run test
./run test -- -v -k condition
```

- **~320 tests** in `tests/pixil/` (see `COVERAGE.md`)
- Imports `pixil_utils` only — not `Pixil.py` at runtime
- Prefer new tests here for logic you can assert in Python

### Python for `./run test`

Resolved in order: `$PIXIL_PYTHON`, `./python_venv`, `../python_venv`, legacy path, then system `python3` with apt pytest.

On Debian/Raspberry Pi OS, use **`./run setup-tests`** (apt). Avoid `pip install pytest` on system Python.

## Tier 2: script smoke tests

Full documentation: **[tests/scripts/README.md](scripts/README.md)** and **[tests/scripts/golden/README.md](scripts/golden/README.md)**.

```bash
./run test-scripts   # compare goldens; create .hash files only when missing
PIXIL_TEST_UPDATE_GOLDEN=1 ./run test-scripts   # overwrite all non-volatile goldens
```

### Manifest

Edit `tests/scripts/manifest/core.txt`:

```
testing/test_math.pix
testing/test_datetime.pix volatile
```

- Path is relative to `scripts/`
- Second token `volatile` = run script but **do not** compare buffer goldens (live clock/runtime)

### Goldens

After a deterministic script is in the manifest:

1. `./run test-scripts` on the Pi (writes `golden/<name>.hash` if missing)
2. Commit `tests/scripts/golden/<name>.hash` (one line: `empty` or 16 hex chars)
3. Later `./run test-scripts` compares automatically; use `PIXIL_TEST_UPDATE_GOLDEN=1` only to refresh after visual changes

### Adding tests when you change code

| You changed | Do this |
|-------------|---------|
| `pixil_utils` math/conditions/params | Add `tests/pixil/test_*.py` |
| Drawing / sprites / frames | Add `scripts/testing/*.pix` + manifest line + golden |
| Live time on matrix | Manifest with `volatile`; no golden file |

## Tier 3 (future)

`tests/rgb_matrix/` is reserved for simulated-matrix or deep `rgb_matrix_lib` tests without flashing LEDs. Not implemented yet; Tier 2 is the hardware integration check.

## Legacy

- **`scripts/test_regression.pix`** — manual visual regression; not run by `./run test`
- **`_python_tests/`** — old experiments; not collected by pytest. New work goes under `tests/`.

## Related source (test-only paths)

| File | Role |
|------|------|
| `pixil_utils/test_hooks.py` | Metrics, `rest()` cap, `PIXIL_TEST_SUMMARY` |
| `rgb_matrix_lib/test_inspect.py` | Buffer fingerprint + optional state file |
| `shared/command_queue.py` | `__test_snapshot__` in consumer; IPC reply queue |
