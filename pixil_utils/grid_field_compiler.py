"""Parse grid_program and field_program blocks into compiled specs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .grid_expr import ExprNode, parse_expr

_ASSIGN_RE = re.compile(r"^(v_\w+)\s*=\s*(.+)$")
_STEP_RE = re.compile(r"^step\s+(v_\w+)\s*\{$")
_DRAW_RE = re.compile(r"^draw\s*\{$")
_VALUE_RE = re.compile(r"^value\s*\{$")


@dataclass
class StepBlock:
    field: str
    assignments: List[Tuple[str, ExprNode]]


@dataclass
class GridDrawSpec:
    mode: str = "palette"
    palette_field: Optional[str] = None
    color_base: str = "1"
    color_scale: str = "65"
    intensity_base: str = "28"
    intensity_scale: str = "72"
    fill_field: Optional[str] = None
    fill_color: str = "cyan"
    fill_intensity: str = "90"
    fire_field: Optional[str] = None
    plot_if: Optional[ExprNode] = None
    color_expr: Optional[ExprNode] = None
    opacity_expr: Optional[ExprNode] = None


@dataclass
class GridProgram:
    name: str
    size: str = "32"
    cell: str = "1"
    fields: List[str] = field(default_factory=list)
    steps: str = "1"
    boundary: str = "clamp"
    step_blocks: List[StepBlock] = field(default_factory=list)
    draw: GridDrawSpec = field(default_factory=GridDrawSpec)


@dataclass
class FieldProgram:
    name: str
    size: str = "64"
    sites_x: str = ""
    sites_y: str = ""
    weights: Optional[str] = None
    phases: Optional[str] = None
    active: Optional[str] = None
    mode: str = "formula"
    value_assignments: List[Tuple[str, ExprNode]] = field(default_factory=list)
    value_result: Optional[str] = None
    plot_if: Optional[ExprNode] = None
    color_expr: Optional[ExprNode] = None
    opacity_expr: Optional[ExprNode] = None
    signed: bool = False
    peak_color: str = "cyan"
    trough_color: str = "blue"
    intensity_scale: str = "35"
    edges: bool = False
    edge_ratio: str = "1.05"
    site_colors: Optional[str] = None
    edge_color: str = "white"
    edge_opacity: str = "90"
    fill_opacity: str = "60"


def collect_brace_block_lines(line_iter) -> List[str]:
    """Consume lines from a generator until the outermost `{` block closes."""
    body: List[str] = []
    depth = 1
    for raw_line in line_iter:
        stripped = raw_line.strip()
        open_count = stripped.count("{")
        close_count = stripped.count("}")
        new_depth = depth + open_count - close_count
        if new_depth <= 0:
            depth = 0
            break
        body.append(stripped)
        depth = new_depth
    if depth > 0:
        raise ValueError("Unclosed block")
    return body


def _collect_brace_block(lines: List[str], start: int) -> Tuple[List[str], int]:
    """Collect lines inside an already-opened `{` block; start points at header line."""
    body: List[str] = []
    i = start + 1
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "}":
            return body, i + 1
        body.append(stripped)
        i += 1
    raise ValueError("Unclosed block")


def _parse_assignments(body: List[str]) -> List[Tuple[str, ExprNode]]:
    assignments: List[Tuple[str, ExprNode]] = []
    for line in body:
        if not line:
            continue
        match = _ASSIGN_RE.match(line)
        if not match:
            raise ValueError(f"Expected assignment in block, got: {line}")
        target, expr_text = match.group(1), match.group(2).strip()
        assignments.append((target, parse_expr(expr_text)))
    return assignments


def _parse_draw_body(body: List[str]) -> GridDrawSpec:
    spec = GridDrawSpec()
    for line in body:
        if not line:
            continue
        parts = line.split(None, 1)
        key = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ""
        if key == "palette_field":
            spec.mode = "palette"
            spec.palette_field = rest
        elif key == "color_base":
            spec.color_base = rest
        elif key == "color_scale":
            spec.color_scale = rest
        elif key == "intensity_base":
            spec.intensity_base = rest
        elif key == "intensity_scale":
            spec.intensity_scale = rest
        elif key == "fill_field":
            spec.mode = "fill"
            spec.fill_field = rest
        elif key == "fill_color":
            spec.fill_color = rest
        elif key == "fill_intensity":
            spec.fill_intensity = rest
        elif key == "fire_field":
            spec.mode = "fire"
            spec.fire_field = rest
        elif key == "plot_if":
            spec.mode = "expr"
            spec.plot_if = parse_expr(rest)
        elif key == "color":
            spec.color_expr = parse_expr(rest)
        elif key == "opacity":
            spec.opacity_expr = parse_expr(rest)
        else:
            raise ValueError(f"Unknown draw directive: {key}")
    return spec


def compile_grid_program(name: str, body_lines: List[str]) -> GridProgram:
    program = GridProgram(name=name)
    i = 0
    while i < len(body_lines):
        line = body_lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("size "):
            program.size = line.split(None, 1)[1].strip()
        elif line.startswith("cell "):
            program.cell = line.split(None, 1)[1].strip()
        elif line.startswith("fields "):
            raw = line.split(None, 1)[1].strip()
            program.fields = [f.strip() for f in raw.split(",") if f.strip()]
        elif line.startswith("steps "):
            program.steps = line.split(None, 1)[1].strip()
        elif line.startswith("boundary "):
            program.boundary = line.split(None, 1)[1].strip()
        elif _STEP_RE.match(line):
            field_name = _STEP_RE.match(line).group(1)
            block_body, i = _collect_brace_block(body_lines, i)
            program.step_blocks.append(
                StepBlock(field=field_name, assignments=_parse_assignments(block_body))
            )
            continue
        elif _DRAW_RE.match(line):
            block_body, i = _collect_brace_block(body_lines, i)
            program.draw = _parse_draw_body(block_body)
            continue
        else:
            raise ValueError(f"Unknown grid_program directive: {line}")
        i += 1

    if not program.fields:
        raise ValueError(f"grid_program {name}: fields required")
    if not program.step_blocks:
        raise ValueError(f"grid_program {name}: at least one step block required")
    return program


def compile_field_program(name: str, body_lines: List[str]) -> FieldProgram:
    program = FieldProgram(name=name)
    i = 0
    while i < len(body_lines):
        line = body_lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith("size "):
            program.size = line.split(None, 1)[1].strip()
        elif line.startswith("sites "):
            raw = line.split(None, 1)[1].strip()
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            if len(parts) != 2:
                raise ValueError("sites requires two arrays: sites x_arr, y_arr")
            program.sites_x, program.sites_y = parts
        elif line.startswith("weights "):
            program.weights = line.split(None, 1)[1].strip()
        elif line.startswith("phases "):
            program.phases = line.split(None, 1)[1].strip()
        elif line.startswith("active "):
            program.active = line.split(None, 1)[1].strip()
        elif line.startswith("signed "):
            program.signed = line.split(None, 1)[1].strip().lower() == "true"
        elif line.startswith("peak_color "):
            program.peak_color = line.split(None, 1)[1].strip()
        elif line.startswith("trough_color "):
            program.trough_color = line.split(None, 1)[1].strip()
        elif line.startswith("intensity_scale "):
            program.intensity_scale = line.split(None, 1)[1].strip()
        elif line.startswith("mode "):
            program.mode = line.split(None, 1)[1].strip()
        elif line.startswith("plot_if "):
            program.plot_if = parse_expr(line.split(None, 1)[1].strip())
        elif line.startswith("color "):
            program.color_expr = parse_expr(line.split(None, 1)[1].strip())
        elif line.startswith("opacity "):
            program.opacity_expr = parse_expr(line.split(None, 1)[1].strip())
        elif line.startswith("edges "):
            program.edges = line.split(None, 1)[1].strip().lower() == "true"
        elif line.startswith("edge_ratio "):
            program.edge_ratio = line.split(None, 1)[1].strip()
        elif line.startswith("site_colors "):
            program.site_colors = line.split(None, 1)[1].strip()
        elif line.startswith("edge_color "):
            program.edge_color = line.split(None, 1)[1].strip()
        elif line.startswith("edge_opacity "):
            program.edge_opacity = line.split(None, 1)[1].strip()
        elif line.startswith("fill_opacity "):
            program.fill_opacity = line.split(None, 1)[1].strip()
        elif _VALUE_RE.match(line):
            block_body, i = _collect_brace_block(body_lines, i)
            program.value_assignments = _parse_assignments(block_body)
            if program.value_assignments:
                program.value_result = program.value_assignments[-1][0]
            continue
        else:
            raise ValueError(f"Unknown field_program directive: {line}")
        i += 1

    if not program.sites_x or not program.sites_y:
        raise ValueError(f"field_program {name}: sites required")
    return program
