"""Shared math expression cases for Tier 1 catalog tests (JIT-off production paths)."""

import math

# (expression, expected) — uses default variables fixture: v_x=10, v_y=5, v_z=15, v_a=1, v_b=0
MATH_EXPR_CASES = [
    ("cos(0)", 1.0),
    ("sin(0)", 0.0),
    ("tan(0)", 0.0),
    ("abs(-7)", 7),
    ("pow(2, 3)", 8),
    ("sqrt(9)", 3.0),
    ("exp(0)", 1.0),
    ("log(1)", 0.0),
    ("log10(100)", 2.0),
    ("trunc(3.9)", 3),
    ("int(3.9)", 3),
    ("asin(0)", 0.0),
    ("acos(1)", 0.0),
    ("atan(0)", 0.0),
    ("atan2(1, 1)", math.pi / 4),
    ("degrees(pi)", 180.0),
    ("radians(180)", math.pi),
    ("min(3, 7)", 3),
    ("max(3, 7)", 7),
    ("pi", math.pi),
    ("e", math.e),
    ("tau", math.tau),
    ("copysign(1, -1)", -1.0),
    ("fabs(-4.5)", 4.5),
    ("remainder(7, 3)", 1.0),
    ("fmod(7, 3)", 1.0),
]

# Fast-path expressions (ENABLE_FAST_MATH); still valid when fast path misses
FAST_MATH_CASES = [
    ("42", 42),
    ("3.5", 3.5),
    ("v_x + 5", 15),
    ("v_x * 2", 20),
    ("v_x - 3", 7),
    ("v_x / 2", 5.0),
    ("v_x % 3", 1),
    ("5 + v_x", 15),
    ("2 * v_x", 20),
]
