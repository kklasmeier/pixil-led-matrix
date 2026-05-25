"""Condition strings ported from scripts/testing/test_parentheses_conditions.pix."""

# (condition, expected) with legacy_condition_vars: v_x=10, v_y=5, v_z=15, v_a=1, v_b=0
LEGACY_CONDITION_CASES = [
    ("v_x > 5", True),
    ("v_z == 15", True),
    ("v_x > 5 and v_y < 10", True),
    ("v_x > 100 or v_y < 10", True),
    ("v_a == 1 or v_b == 1 and v_z == 0", True),
    ("v_x > 5 and v_y < 10 and v_z == 15", True),
    ("v_x > 100 or v_y > 100 or v_z == 15", True),
    ("v_a", True),
    ("v_b", False),
    ("v_x != 5", True),
    ("v_y <= 5", True),
    ("v_x >= 10", True),
    ("(v_x > 100) or (v_y < 10)", True),
    ("(v_x > 5) and (v_y < 3)", False),
    ("v_x > 5 and v_y > 100 and v_z == 15", False),
    ("v_x > 100 or v_y > 100 or v_z == 0 or v_a == 99", False),
    ("v_x > 5 and v_y < 10 or v_z == 0 and v_a == 99", True),
    ("(v_x > 5 or v_y < 2) and v_z == 15", True),
    ("(v_x > 20 and v_y < 2) or v_z == 15", True),
    ("(v_x > 5 and v_y < 10) or (v_z == 0)", True),
    ("(v_x > 5) and (v_z == 15)", True),
    ("(v_a == 1 or v_b == 1) and v_z == 0", False),
    ("(v_x > 5) or (v_y > 100) or (v_z == 15)", True),
    ("v_a == 1 and (v_x > 5 or v_y > 100)", True),
    ("not v_b == 1", True),
    ("not v_a == 1", False),
    ("not (v_x > 5 and v_y < 10)", False),
    ("v_a == 1 and not v_b == 1", True),
    ("v_x > 100 or not v_b == 1", True),
    ("not (v_x > 100 or v_y > 100)", True),
    ("(v_x > 5) and not (v_y > 100 or v_z == 0)", True),
]

# Extra setup applied before evaluate: {var: value, ...}
CONDITION_WITH_SETUP = [
    ('v_color == "red"', True, {"v_color": "red"}),
    ('v_color != "blue"', True, {"v_color": "red"}),
    ('v_color == "green"', False, {"v_color": "red"}),
    ('v_color == "red" and v_x > 5', True, {"v_color": "red"}),
    ('v_color == "blue" or v_x > 5', True, {"v_color": "red"}),
    ('not v_color == "blue"', True, {"v_color": "red"}),
]
