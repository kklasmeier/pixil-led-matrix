# Tier 3: rgb_matrix_lib tests (planned)

Tests here will use a **simulated matrix** (in-memory numpy buffer) so rendering logic can be asserted without the LED panel.

Production `rgb_matrix_lib/api.py` will not import test code. The simulated API will live under `tests/rgb_matrix/` or `tests/support/` and be used only by pytest.

Until that exists, rendering changes are validated manually on hardware.
