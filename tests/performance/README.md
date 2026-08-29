# Particle primitive performance POC

This benchmark compares identical deterministic particle simulations:

- `scripts/testing/perf_particle_reference.pix` implements integration, bounds,
  and circle collisions in Pixil.
- `scripts/testing/perf_particle_primitives.pix` uses the generic
  `particle_*` commands.

Run it on the matrix Pi while the regular show is stopped:

```bash
python3 tests/performance/run_particle_primitives_poc.py
```

The runner alternates execution order, runs each variant three times, and
reports median elapsed time. It fails unless:

- both scripts complete the same number of frames;
- their final-state checksums differ by no more than `0.01`;
- primitives are at least `1.5x` faster.

Options:

```bash
python3 tests/performance/run_particle_primitives_poc.py \
  --runs 5 --min-speedup 2.0
```

This is intentionally not part of `./run test`: it requires passwordless sudo
and exclusive access to the LED matrix, and timing assertions should not make
normal unit tests flaky.
