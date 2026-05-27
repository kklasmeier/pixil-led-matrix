# Tier 1 test coverage map

| Test file | Module(s) | Covers |
|-----------|-----------|--------|
| `test_variable_registry.py` | `variable_registry.py` | register/get/set, dict API, fast array access/assign |
| `test_assignment_semantics.py` | `math_functions.py`, `array_manager.py` | v_=expr semantics, array size/flat index (Pixil assignment path) |
| `test_arrays.py` | `array_manager.py` | PixilArray numeric/string, bounds, validate_array_access |
| `test_math_expressions.py` | `math_functions.py` | evaluate_math_expression, fast paths, has_math_expression |
| `test_math_depth.py` | `math_functions.py` | split_outside_quotes, compound datetime, nested arrays, log/atan |
| `test_math_catalog.py` | `math_functions.py` | MATH_FUNCTIONS catalog, fast paths, substitute_variables |
| `test_conditions.py` | `math_functions.py` | evaluate_condition, compound/paren/not, error messages |
| `test_condition_templates.py` | `condition_templates.py` | fast path + legacy 1–6 from parentheses test script |
| `test_condition_parity.py` | `condition_templates.py`, `math_functions.py` | Legacy/paren port + fast/full parity + error cases |
| `test_string_and_datetime.py` | `math_functions.py` | concat, get_datetime, get_system |
| `test_parameter_splitting.py` | `parameter_types.py` | split_command_parameters |
| `test_parameter_types.py` | `parameter_types.py` | convert, validate, `parse_bool_literal`, `begin_frame` |
| `test_parameter_commands.py` | `parameter_types.py` | minimal params for **all** commands |
| `test_parameter_errors.py` | `parameter_types.py` | too few/many params, invalid conversions |
| `test_expression_parser.py` | `expression_parser.py` | colors, format_parameter, escape, draw_text |
| `test_jit_compiler.py` | `jit_compiler/` | dormant-path guard (JIT off in production) |
| `test_loop_compiler.py` | `loop_compiler.py` | compile/run mplot grids, draw_* in loops, elseif, array assign, `begin_frame(false)`, Chladni-style frame+plot, reject call in loops |
| `test_draw_batch_protocol.py` | `draw_batch_protocol.py`, `draw_batch_dispatch.py` | pack/unpack plot+shapes, string coords (plot/mplot), submission order |
| `test_procedure_compiler.py` | `loop_compiler.py` | procedures: call, array assign, if/else, begin_frame |
| `test_compiled_blocks.py` | `loop_compiler.py` | flag gating, elseif execution, Boids compile smoke, mplot named/expression colors |
| `test_script_manager.py` | `script_manager.py`, `file_manager.py` | path resolution, glob |
| `test_shape_param_shorthand.py` | `parameter_types.py` | expand_legacy + format_parameter for rectangle/circle/polygon/ellipse (legacy + full forms) |
| `test_small_modules.py` | `cli.py`, `timer_manager.py`, `optimization_flags.py`, `regex_patterns.py`, `debug.py` | validators, timer, flags, regex smoke |
| `_math_cases.py`, `_condition_cases.py` | — | shared parametrized case tables |

**Tier 2:** `tests/scripts/manifest/core.txt` + optional `main_smoke.txt` via `./run test-scripts` / `test-all`  
Harness: `run_script_tests.py` (per-script `-t`, PASS/FAIL via `PIXIL_TEST_SUMMARY`).  
Unit tests: `test_script_manifest.py` (manifest parsing, no LED).  
Main smokes: 6–8s each in `main_smoke.txt` (not 1:00). See `tests/scripts/README.md`.

## Not yet covered

- `Pixil.py` `process_script` / `parse_value` (Tier 2 / future extract-on-touch)
- `terminal_handler.py` (interactive stdin; headless no-ops in `Pixil.py`)
- Exhaustive `condition_templates.py` template-class branches (parity table covers common script shapes)
- `rgb_matrix_lib/` (Tier 3 / Tier 2)
- **JIT expansion** — intentionally frozen; `test_jit_compiler.py` only

## Run

```bash
./run test                    # ~300+ tests, <2s typical
./run test -- -v -k catalog   # math catalog only
```
