"""
Compiled block bodies (loops v0, procedures v0).

Parses a block once into a small statement tree, then runs it without re-dispatching
lines through process_lines.

Loops: nested for (literal bounds folded at compile time), v_ assignments, array assigns,
       if/elseif/else, break, mplot(...), plot(...) (fast path), draw_line/draw_circle
       (fast path), other draw_* via CommandStmt.
Procedures: loops plus array assign, if/elseif/else, call/bare proc name,
            begin_frame, end_frame, mflush, plot, draw_line, draw_circle, draw_polygon, etc.
Unsupported constructs cause compile failure and interpreter fallback.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple

from .regex_patterns import (
    FOR_LOOP_PATTERN,
    WHILE_LOOP_PATTERN,
    COMMAND_PATTERN,
    PROCEDURE_CALL_PATTERN,
    ARRAY_ASSIGN_PATTERN,
    NUMBER_PATTERN,
)
from . import optimization_flags
from .math_functions import evaluate_math_expression, evaluate_condition, has_math_expression
from .condition_templates import evaluate_condition_fast
from .jit_compiler import ExpressionCompiler, PixilVM, PixilVMError
from .array_manager import PixilArray
from shared.mplot_protocol import BURNOUT_MODE_TO_INT, NAMED_COLOR_TO_ID

_expr_compiler = ExpressionCompiler()
_loop_vm = PixilVM()
_LOOP_BODY_CACHE: dict[tuple[str, ...], "CompiledBlock"] = {}
_PROCEDURE_BODY_CACHE: dict[tuple[str, ...], "CompiledBlock"] = {}

# Stats (reset per script in Pixil.py)
COMPILED_LOOP_ATTEMPTS = 0
COMPILED_LOOP_HITS = 0
COMPILED_LOOP_FALLBACKS = 0
COMPILED_LOOP_ITERATIONS = 0
COMPILED_PROC_ATTEMPTS = 0
COMPILED_PROC_HITS = 0
COMPILED_PROC_FALLBACKS = 0
COMPILED_PROC_CALLS = 0

_FRAME_COMMANDS = frozenset({
    "draw_line", "draw_circle", "draw_rectangle", "plot", "draw_ellipse", "draw_polygon",
})
_FRAME_NO_ARG = frozenset({"begin_frame", "end_frame", "mflush", "hide_background", "clear"})
_FRAME_MISC_COMMANDS = frozenset({"fps"})
# Must not be treated as bare procedure names (e.g. begin_frame has no parens in scripts)
_FRAME_BUILTIN_NAMES = _FRAME_NO_ARG | _FRAME_COMMANDS | _FRAME_MISC_COMMANDS
_SPRITE_COMMANDS = frozenset({"show_sprite", "move_sprite", "hide_sprite"})
_BARE_CALL_RESERVED = frozenset(
    {"else", "break", "endif", "endfor", "endwhile", "endsprite", "then", "true", "false"}
)


class LoopBreak(Exception):
    """Exit the innermost compiled for/while loop body."""


def _run_body(statements: List["Statement"], ctx: ExecContext) -> None:
    """Run a statement list; LoopBreak propagates to the enclosing for/while."""
    for stmt in statements:
        stmt.run(ctx)


def reset_loop_compiler_stats() -> None:
    global COMPILED_LOOP_ATTEMPTS, COMPILED_LOOP_HITS, COMPILED_LOOP_FALLBACKS
    global COMPILED_LOOP_ITERATIONS, COMPILED_PROC_ATTEMPTS, COMPILED_PROC_HITS
    global COMPILED_PROC_FALLBACKS, COMPILED_PROC_CALLS
    COMPILED_LOOP_ATTEMPTS = 0
    COMPILED_LOOP_HITS = 0
    COMPILED_LOOP_FALLBACKS = 0
    COMPILED_LOOP_ITERATIONS = 0
    COMPILED_PROC_ATTEMPTS = 0
    COMPILED_PROC_HITS = 0
    COMPILED_PROC_FALLBACKS = 0
    COMPILED_PROC_CALLS = 0
    _LOOP_BODY_CACHE.clear()
    _PROCEDURE_BODY_CACHE.clear()


def _precompile_expression(expr: str) -> Optional[Any]:
    if not optimization_flags.ENABLE_COMPILED_LOOP_EXPR:
        return None
    try:
        return _expr_compiler.compile(expr)
    except Exception:
        return None


def _eval_expression(expr: str, compiled: Optional[Any], ctx: "ExecContext") -> Any:
    if compiled is not None:
        try:
            return _loop_vm.execute(compiled, ctx.variables)
        except PixilVMError:
            pass
    return ctx.eval_expr(expr)


def _eval_mplot_color(color_expr: str, compiled: Optional[Any], ctx: "ExecContext") -> Any:
    """Resolve mplot color like parse_value: named colors pass through, expressions evaluate.

    Pixil scripts sometimes use quoted named colors (e.g. `"white"`). The interpreter
    path strips those quotes via `format_parameter()`; compiled blocks should too.
    """
    s = color_expr.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()

    lower = s.lower()
    if lower in NAMED_COLOR_TO_ID:
        return lower
    if NUMBER_PATTERN.match(s):
        return float(s) if "." in s else int(s)
    if s.startswith("v_") or has_math_expression(s):
        result = _eval_expression(s, compiled, ctx)
        if isinstance(result, str) and (
            (result.startswith('"') and result.endswith('"'))
            or (result.startswith("'") and result.endswith("'"))
        ):
            result = result[1:-1]
        return result
    return s


def _eval_burnout_mode(mode_expr: str, compiled: Optional[Any], ctx: "ExecContext") -> Any:
    """Resolve mplot burnout_mode: instant/fade literals, not math identifiers."""
    s = mode_expr.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    lower = s.lower()
    if lower in BURNOUT_MODE_TO_INT:
        return lower
    if s.startswith("v_") or has_math_expression(s):
        result = _eval_expression(s, compiled, ctx)
        if isinstance(result, str):
            return result.strip('"').strip("'").lower()
        return result
    return s


def _eval_bool_literal(bool_expr: str, compiled: Optional[Any], ctx: "ExecContext") -> bool:
    """Resolve true/false literals or expressions for shape filled parameters."""
    s = bool_expr.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1].strip()
    lower = s.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if s.startswith("v_") or has_math_expression(s):
        result = _eval_expression(s, compiled, ctx)
        if isinstance(result, bool):
            return result
        if isinstance(result, (int, float)):
            return bool(result)
        if isinstance(result, str):
            return result.strip().lower() == "true"
    from .parameter_types import parse_bool_literal
    return parse_bool_literal(s)


def _is_bool_token(value: str) -> bool:
    return value.strip().lower() in ("true", "false")


def get_loop_compiler_stats() -> dict:
    return {
        "compiled_loop_attempts": COMPILED_LOOP_ATTEMPTS,
        "compiled_loop_hits": COMPILED_LOOP_HITS,
        "compiled_loop_fallbacks": COMPILED_LOOP_FALLBACKS,
        "compiled_loop_iterations": COMPILED_LOOP_ITERATIONS,
        "compiled_proc_attempts": COMPILED_PROC_ATTEMPTS,
        "compiled_proc_hits": COMPILED_PROC_HITS,
        "compiled_proc_fallbacks": COMPILED_PROC_FALLBACKS,
        "compiled_proc_calls": COMPILED_PROC_CALLS,
    }


@dataclass
class ExecContext:
    variables: Any
    eval_expr: Callable[[str], Any]
    eval_cond: Callable[[str], bool]
    mplot: Callable[..., None]
    is_expired: Callable[[], bool]
    call_procedure: Optional[Callable[[str], None]] = None
    run_command: Optional[Callable[[str, List[str]], None]] = None
    plot: Optional[Callable[..., None]] = None
    draw_line: Optional[Callable[..., None]] = None
    draw_circle: Optional[Callable[..., None]] = None


# Backward-compatible alias
LoopContext = ExecContext


@dataclass
class CompiledBlock:
    statements: List["Statement"]


# Legacy alias
CompiledLoopBody = CompiledBlock


class Statement:
    def run(self, ctx: ExecContext) -> None:
        raise NotImplementedError


@dataclass
class BreakStmt(Statement):
    def run(self, ctx: ExecContext) -> None:
        raise LoopBreak()


@dataclass
class AssignStmt(Statement):
    var: str
    expr: str
    compiled_expr: Optional[Any] = field(default=None, repr=False)

    def run(self, ctx: ExecContext) -> None:
        ctx.variables.set(self.var, _eval_expression(self.expr, self.compiled_expr, ctx))


@dataclass
class ArrayAssignStmt(Statement):
    array: str
    index_expr: str
    value_expr: str
    compiled_index: Optional[Any] = field(default=None, repr=False)
    compiled_value: Optional[Any] = field(default=None, repr=False)

    def run(self, ctx: ExecContext) -> None:
        arr = ctx.variables.get(self.array)
        if not isinstance(arr, PixilArray):
            raise ValueError(f"Variable '{self.array}' is not an array")
        index = int(float(_eval_expression(self.index_expr, self.compiled_index, ctx)))
        value = _eval_expression(self.value_expr, self.compiled_value, ctx)
        arr[index] = value


@dataclass
class IfStmt(Statement):
    branches: List[Tuple[Optional[str], List[Statement]]]

    def run(self, ctx: ExecContext) -> None:
        for condition, body in self.branches:
            if condition is None:
                _run_body(body, ctx)
                return
            if ctx.eval_cond(condition):
                _run_body(body, ctx)
                return


def _try_literal_float(expr: str) -> Optional[float]:
    """Return float when expr is a numeric literal (e.g. 0, 63, 1)."""
    s = expr.strip()
    if NUMBER_PATTERN.match(s):
        return float(s)
    return None


def _make_for_stmt(
    loop_var: str,
    start_e: str,
    end_e: str,
    step_e: str,
    body: List[Statement],
) -> "ForStmt":
    cs = _try_literal_float(start_e)
    ce = _try_literal_float(end_e)
    cst = _try_literal_float(step_e)
    if cs is not None and ce is not None and cst is not None:
        return ForStmt(loop_var, start_e, end_e, step_e, body, cs, ce, cst)
    return ForStmt(loop_var, start_e, end_e, step_e, body)


@dataclass
class ForStmt(Statement):
    loop_var: str
    start_expr: str
    end_expr: str
    step_expr: str
    body: List[Statement]
    const_start: Optional[float] = field(default=None, repr=False)
    const_end: Optional[float] = field(default=None, repr=False)
    const_step: Optional[float] = field(default=None, repr=False)

    def _resolve_bounds(self, ctx: ExecContext) -> tuple[float, float, float]:
        if self.const_start is not None:
            return self.const_start, self.const_end, self.const_step  # type: ignore[return-value]
        return (
            float(ctx.eval_expr(self.start_expr)),
            float(ctx.eval_expr(self.end_expr)),
            float(ctx.eval_expr(self.step_expr)),
        )

    def run(self, ctx: ExecContext) -> None:
        start, end, step = self._resolve_bounds(ctx)
        epsilon = 1e-10
        current = start
        while (step > 0 and current <= end + epsilon) or (step < 0 and current >= end - epsilon):
            if ctx.is_expired():
                break
            ctx.variables.set(self.loop_var, current)
            try:
                _run_body(self.body, ctx)
            except LoopBreak:
                break
            global COMPILED_LOOP_ITERATIONS
            COMPILED_LOOP_ITERATIONS += 1
            current += step


@dataclass
class WhileStmt(Statement):
    condition: str

    body: List[Statement]

    def run(self, ctx: ExecContext) -> None:
        while True:
            if ctx.is_expired():
                break
            if not ctx.eval_cond(self.condition):
                break
            try:
                _run_body(self.body, ctx)
            except LoopBreak:
                break
            global COMPILED_LOOP_ITERATIONS
            COMPILED_LOOP_ITERATIONS += 1


@dataclass
class MplotStmt(Statement):
    x_expr: str
    y_expr: str
    color_expr: str
    intensity_expr: str
    burnout_expr: Optional[str] = None
    burnout_mode_expr: Optional[str] = None
    compiled_x: Optional[Any] = field(default=None, repr=False)
    compiled_y: Optional[Any] = field(default=None, repr=False)
    compiled_color: Optional[Any] = field(default=None, repr=False)
    compiled_intensity: Optional[Any] = field(default=None, repr=False)
    compiled_burnout: Optional[Any] = field(default=None, repr=False)
    compiled_burnout_mode: Optional[Any] = field(default=None, repr=False)

    def run(self, ctx: ExecContext) -> None:
        x = int(float(_eval_expression(self.x_expr, self.compiled_x, ctx)))
        y = int(float(_eval_expression(self.y_expr, self.compiled_y, ctx)))
        if not (0 <= x <= 63 and 0 <= y <= 63):
            return
        color = _eval_mplot_color(self.color_expr, self.compiled_color, ctx)
        intensity = int(float(_eval_expression(self.intensity_expr, self.compiled_intensity, ctx)))
        burnout = None
        if self.burnout_expr is not None:
            burnout = int(float(_eval_expression(self.burnout_expr, self.compiled_burnout, ctx)))
        burnout_mode = None
        if self.burnout_mode_expr is not None:
            burnout_mode = _eval_burnout_mode(
                self.burnout_mode_expr, self.compiled_burnout_mode, ctx,
            )
        if burnout is not None or burnout_mode is not None:
            ctx.mplot(x, y, color, intensity, burnout, burnout_mode)
        else:
            ctx.mplot(x, y, color, intensity)


@dataclass
class PlotStmt(Statement):
    """Fast compiled path for plot(x, y, color, [intensity], [burnout], [burnout_mode])."""

    x_expr: str
    y_expr: str
    color_expr: str
    intensity_expr: str
    burnout_expr: Optional[str] = None
    burnout_mode_expr: Optional[str] = None
    compiled_x: Optional[Any] = field(default=None, repr=False)
    compiled_y: Optional[Any] = field(default=None, repr=False)
    compiled_color: Optional[Any] = field(default=None, repr=False)
    compiled_intensity: Optional[Any] = field(default=None, repr=False)
    compiled_burnout: Optional[Any] = field(default=None, repr=False)
    compiled_burnout_mode: Optional[Any] = field(default=None, repr=False)

    def run(self, ctx: ExecContext) -> None:
        x = int(float(_eval_expression(self.x_expr, self.compiled_x, ctx)))
        y = int(float(_eval_expression(self.y_expr, self.compiled_y, ctx)))
        if not (0 <= x <= 63 and 0 <= y <= 63):
            return
        color = _eval_mplot_color(self.color_expr, self.compiled_color, ctx)
        intensity = int(float(_eval_expression(self.intensity_expr, self.compiled_intensity, ctx)))
        burnout = None
        if self.burnout_expr is not None:
            burnout = int(float(_eval_expression(self.burnout_expr, self.compiled_burnout, ctx)))
        burnout_mode = None
        if self.burnout_mode_expr is not None:
            burnout_mode = _eval_burnout_mode(
                self.burnout_mode_expr, self.compiled_burnout_mode, ctx,
            )
        plot_fn = ctx.plot if ctx.plot is not None else ctx.mplot
        if burnout is not None or burnout_mode is not None:
            plot_fn(x, y, color, intensity, burnout, burnout_mode)
        else:
            plot_fn(x, y, color, intensity)


@dataclass
class DrawLineStmt(Statement):
    """Fast compiled path for draw_line(x0, y0, x1, y1, color, [intensity], ...)."""

    x0_expr: str
    y0_expr: str
    x1_expr: str
    y1_expr: str
    color_expr: str
    intensity_expr: str
    burnout_expr: Optional[str] = None
    burnout_mode_expr: Optional[str] = None
    compiled_x0: Optional[Any] = field(default=None, repr=False)
    compiled_y0: Optional[Any] = field(default=None, repr=False)
    compiled_x1: Optional[Any] = field(default=None, repr=False)
    compiled_y1: Optional[Any] = field(default=None, repr=False)
    compiled_color: Optional[Any] = field(default=None, repr=False)
    compiled_intensity: Optional[Any] = field(default=None, repr=False)
    compiled_burnout: Optional[Any] = field(default=None, repr=False)
    compiled_burnout_mode: Optional[Any] = field(default=None, repr=False)

    def run(self, ctx: ExecContext) -> None:
        x0 = int(float(_eval_expression(self.x0_expr, self.compiled_x0, ctx)))
        y0 = int(float(_eval_expression(self.y0_expr, self.compiled_y0, ctx)))
        x1 = int(float(_eval_expression(self.x1_expr, self.compiled_x1, ctx)))
        y1 = int(float(_eval_expression(self.y1_expr, self.compiled_y1, ctx)))
        color = _eval_mplot_color(self.color_expr, self.compiled_color, ctx)
        intensity = int(float(_eval_expression(self.intensity_expr, self.compiled_intensity, ctx)))
        burnout = None
        if self.burnout_expr is not None:
            burnout = int(float(_eval_expression(self.burnout_expr, self.compiled_burnout, ctx)))
        burnout_mode = None
        if self.burnout_mode_expr is not None:
            burnout_mode = _eval_burnout_mode(
                self.burnout_mode_expr, self.compiled_burnout_mode, ctx,
            )
        draw_fn = ctx.draw_line
        if draw_fn is None:
            if ctx.run_command is None:
                raise RuntimeError("draw_line not configured")
            args = [self.x0_expr, self.y0_expr, self.x1_expr, self.y1_expr, self.color_expr, self.intensity_expr]
            if self.burnout_expr is not None:
                args.append(self.burnout_expr)
                if self.burnout_mode_expr is not None:
                    args.append(self.burnout_mode_expr)
            ctx.run_command("draw_line", args)
            return
        if burnout is not None or burnout_mode is not None:
            draw_fn(x0, y0, x1, y1, color, intensity, burnout, burnout_mode)
        else:
            draw_fn(x0, y0, x1, y1, color, intensity)


@dataclass
class DrawCircleStmt(Statement):
    """Fast compiled path for draw_circle(x, y, radius, color, [intensity], filled, ...)."""

    x_expr: str
    y_expr: str
    radius_expr: str
    color_expr: str
    intensity_expr: str
    filled_expr: str
    burnout_expr: Optional[str] = None
    burnout_mode_expr: Optional[str] = None
    compiled_x: Optional[Any] = field(default=None, repr=False)
    compiled_y: Optional[Any] = field(default=None, repr=False)
    compiled_radius: Optional[Any] = field(default=None, repr=False)
    compiled_color: Optional[Any] = field(default=None, repr=False)
    compiled_intensity: Optional[Any] = field(default=None, repr=False)
    compiled_filled: Optional[Any] = field(default=None, repr=False)
    compiled_burnout: Optional[Any] = field(default=None, repr=False)
    compiled_burnout_mode: Optional[Any] = field(default=None, repr=False)

    def run(self, ctx: ExecContext) -> None:
        x = int(float(_eval_expression(self.x_expr, self.compiled_x, ctx)))
        y = int(float(_eval_expression(self.y_expr, self.compiled_y, ctx)))
        radius = int(float(_eval_expression(self.radius_expr, self.compiled_radius, ctx)))
        color = _eval_mplot_color(self.color_expr, self.compiled_color, ctx)
        intensity = int(float(_eval_expression(self.intensity_expr, self.compiled_intensity, ctx)))
        filled = _eval_bool_literal(self.filled_expr, self.compiled_filled, ctx)
        burnout = None
        if self.burnout_expr is not None:
            burnout = int(float(_eval_expression(self.burnout_expr, self.compiled_burnout, ctx)))
        burnout_mode = None
        if self.burnout_mode_expr is not None:
            burnout_mode = _eval_burnout_mode(
                self.burnout_mode_expr, self.compiled_burnout_mode, ctx,
            )
        draw_fn = ctx.draw_circle
        if draw_fn is None:
            if ctx.run_command is None:
                raise RuntimeError("draw_circle not configured")
            args = [
                self.x_expr, self.y_expr, self.radius_expr, self.color_expr,
                self.intensity_expr, self.filled_expr,
            ]
            if self.burnout_expr is not None:
                args.append(self.burnout_expr)
                if self.burnout_mode_expr is not None:
                    args.append(self.burnout_mode_expr)
            ctx.run_command("draw_circle", args)
            return
        if burnout is not None or burnout_mode is not None:
            draw_fn(x, y, radius, color, intensity, filled, burnout, burnout_mode)
        else:
            draw_fn(x, y, radius, color, intensity, filled)


@dataclass
class CallStmt(Statement):
    proc_name: str

    def run(self, ctx: ExecContext) -> None:
        if ctx.call_procedure is None:
            raise RuntimeError("call_procedure not configured")
        ctx.call_procedure(self.proc_name)


@dataclass
class CommandStmt(Statement):
    command_name: str
    arg_exprs: List[str]

    def run(self, ctx: ExecContext) -> None:
        if ctx.run_command is None:
            raise RuntimeError("run_command not configured")
        ctx.run_command(self.command_name, self.arg_exprs)


def _parse_plot(line: str) -> Optional[PlotStmt]:
    match = COMMAND_PATTERN.match(line)
    if not match or match.group(1) != "plot":
        return None
    from .parameter_types import split_command_parameters

    args = split_command_parameters(match.group(2))
    if len(args) < 3:
        return None
    intensity_expr = args[3].strip() if len(args) > 3 and args[3].strip() else "100"
    burnout_expr = args[4].strip() if len(args) > 4 and args[4].strip() else None
    burnout_mode_expr = args[5].strip() if len(args) > 5 and args[5].strip() else None
    return PlotStmt(
        args[0], args[1], args[2], intensity_expr,
        burnout_expr, burnout_mode_expr,
        _precompile_expression(args[0]),
        _precompile_expression(args[1]),
        _precompile_expression(args[2]),
        _precompile_expression(intensity_expr),
        _precompile_expression(burnout_expr) if burnout_expr else None,
        _precompile_expression(burnout_mode_expr) if burnout_mode_expr else None,
    )


def _parse_draw_line(line: str) -> Optional[DrawLineStmt]:
    match = COMMAND_PATTERN.match(line)
    if not match or match.group(1) != "draw_line":
        return None
    from .parameter_types import split_command_parameters

    args = split_command_parameters(match.group(2))
    if len(args) < 5:
        return None
    intensity_expr = args[5].strip() if len(args) > 5 and args[5].strip() else "100"
    burnout_expr = args[6].strip() if len(args) > 6 and args[6].strip() else None
    burnout_mode_expr = args[7].strip() if len(args) > 7 and args[7].strip() else None
    return DrawLineStmt(
        args[0], args[1], args[2], args[3], args[4], intensity_expr,
        burnout_expr, burnout_mode_expr,
        _precompile_expression(args[0]),
        _precompile_expression(args[1]),
        _precompile_expression(args[2]),
        _precompile_expression(args[3]),
        _precompile_expression(args[4]),
        _precompile_expression(intensity_expr),
        _precompile_expression(burnout_expr) if burnout_expr else None,
        _precompile_expression(burnout_mode_expr) if burnout_mode_expr else None,
    )


def _parse_draw_circle(line: str) -> Optional[DrawCircleStmt]:
    match = COMMAND_PATTERN.match(line)
    if not match or match.group(1) != "draw_circle":
        return None
    from .parameter_types import split_command_parameters

    args = split_command_parameters(match.group(2))
    if len(args) < 5:
        return None
    if _is_bool_token(args[4]):
        intensity_expr = "100"
        filled_expr = args[4].strip()
        burnout_expr = args[5].strip() if len(args) > 5 and args[5].strip() else None
        burnout_mode_expr = args[6].strip() if len(args) > 6 and args[6].strip() else None
    elif len(args) >= 6:
        intensity_expr = args[4].strip() if args[4].strip() else "100"
        filled_expr = args[5].strip()
        burnout_expr = args[6].strip() if len(args) > 6 and args[6].strip() else None
        burnout_mode_expr = args[7].strip() if len(args) > 7 and args[7].strip() else None
    else:
        return None
    return DrawCircleStmt(
        args[0], args[1], args[2], args[3], intensity_expr, filled_expr,
        burnout_expr, burnout_mode_expr,
        _precompile_expression(args[0]),
        _precompile_expression(args[1]),
        _precompile_expression(args[2]),
        _precompile_expression(args[3]),
        _precompile_expression(intensity_expr),
        _precompile_expression(filled_expr),
        _precompile_expression(burnout_expr) if burnout_expr else None,
        _precompile_expression(burnout_mode_expr) if burnout_mode_expr else None,
    )


def _parse_mplot(line: str) -> Optional[MplotStmt]:
    match = COMMAND_PATTERN.match(line)
    if not match or match.group(1) != "mplot":
        return None
    from .parameter_types import split_command_parameters
    args = split_command_parameters(match.group(2))
    if len(args) < 4:
        return None
    burnout_expr = args[4].strip() if len(args) > 4 and args[4].strip() else None
    burnout_mode_expr = args[5].strip() if len(args) > 5 and args[5].strip() else None
    return MplotStmt(
        args[0], args[1], args[2], args[3],
        burnout_expr, burnout_mode_expr,
        _precompile_expression(args[0]),
        _precompile_expression(args[1]),
        _precompile_expression(args[2]),
        _precompile_expression(args[3]),
        _precompile_expression(burnout_expr) if burnout_expr else None,
        _precompile_expression(burnout_mode_expr) if burnout_mode_expr else None,
    )


def _parse_assign(line: str) -> Optional[AssignStmt]:
    if not line.startswith("v_") or "=" not in line:
        return None
    parts = line.split("=", 1)
    if len(parts) != 2:
        return None
    var = parts[0].strip()
    if "[" in var:
        return None
    expr = parts[1].strip()
    return AssignStmt(var, expr, _precompile_expression(expr))


def _parse_array_assign(line: str) -> Optional[ArrayAssignStmt]:
    match = ARRAY_ASSIGN_PATTERN.match(line)
    if not match:
        return None
    array = match.group(1)
    index_expr = match.group(2).strip()
    value_expr = match.group(3).strip()
    return ArrayAssignStmt(
        array, index_expr, value_expr,
        _precompile_expression(index_expr),
        _precompile_expression(value_expr),
    )


def _parse_if_header(line: str) -> Optional[str]:
    line = line.strip()
    if not line.startswith("if ") or not line.endswith("then"):
        return None
    if line.startswith("elseif ") or line == "else":
        return None
    return line[3:-4].strip()


def _parse_call(line: str) -> Optional[CallStmt]:
    match = PROCEDURE_CALL_PATTERN.match(line.strip())
    if match:
        return CallStmt(match.group(1))
    return None


def _parse_bare_call(line: str, allow_bare: bool) -> Optional[CallStmt]:
    if not allow_bare:
        return None
    name = line.strip()
    if not name or " " in name or "(" in name:
        return None
    if name in _BARE_CALL_RESERVED or name in _FRAME_BUILTIN_NAMES:
        return None
    if name.startswith("v_"):
        return None
    if name.startswith("end") or name.startswith("print"):
        return None
    return CallStmt(name)


def _parse_sprite_command(line: str, allow_commands: bool) -> Optional[CommandStmt]:
    if not allow_commands:
        return None
    stripped = line.strip()
    match = COMMAND_PATTERN.match(stripped)
    if not match:
        return None
    cmd = match.group(1)
    if cmd not in _SPRITE_COMMANDS:
        return None
    from .parameter_types import split_command_parameters

    inner = match.group(2)
    args = [a.strip() for a in split_command_parameters(inner)] if inner.strip() else []
    return CommandStmt(cmd, args)


def _parse_command(line: str, allow_commands: bool) -> Optional[CommandStmt]:
    if not allow_commands:
        return None
    stripped = line.strip()
    base = stripped.rstrip("()")
    if base in _FRAME_NO_ARG:
        return CommandStmt(base, [])
    if stripped.startswith("begin_frame("):
        inner = stripped[len("begin_frame("):-1].strip()
        return CommandStmt("begin_frame", [inner] if inner else [])
    if stripped.startswith("fps("):
        inner = stripped[len("fps("):-1].strip()
        return CommandStmt("fps", [inner] if inner else ["0"])
    sprite = _parse_sprite_command(stripped, allow_commands)
    if sprite is not None:
        return sprite
    match = COMMAND_PATTERN.match(stripped)
    if not match:
        return None
    cmd = match.group(1)
    if cmd not in _FRAME_COMMANDS:
        return None
    args = [a.strip() for a in match.group(2).split(",")] if match.group(2).strip() else []
    return CommandStmt(cmd, args)


def _parse_if_block(
    lines: List[str],
    index: int,
    allow_else: bool,
    allow_call: bool,
    allow_bare_call: bool,
    allow_commands: bool,
    allow_array_assign: bool,
) -> Optional[tuple[IfStmt, int]]:
    line = lines[index].strip()
    cond = _parse_if_header(line)
    if cond is None:
        return None
    i = index + 1
    branches: List[Tuple[Optional[str], List[Statement]]] = []
    current_cond: Optional[str] = cond
    body_lines: List[str] = []
    depth = 1
    n = len(lines)

    while i < n:
        inner = lines[i].strip()
        if inner.startswith("if ") and inner.endswith("then"):
            depth += 1
            body_lines.append(lines[i])
            i += 1
            continue
        if inner == "endif":
            depth -= 1
            if depth == 0:
                parsed = _parse_block(
                    body_lines, 0, allow_else, allow_call, allow_bare_call,
                    allow_commands, allow_array_assign,
                )
                if parsed is None:
                    return None
                branches.append((current_cond, parsed[0]))
                return IfStmt(branches), i + 1
            body_lines.append(lines[i])
            i += 1
            continue
        if depth == 1 and allow_else:
            if inner.startswith("elseif ") and inner.endswith("then"):
                parsed = _parse_block(
                    body_lines, 0, allow_else, allow_call, allow_bare_call,
                    allow_commands, allow_array_assign,
                )
                if parsed is None:
                    return None
                branches.append((current_cond, parsed[0]))
                current_cond = inner[7:-5].strip()
                body_lines = []
                i += 1
                continue
            if inner == "else":
                parsed = _parse_block(
                    body_lines, 0, allow_else, allow_call, allow_bare_call,
                    allow_commands, allow_array_assign,
                )
                if parsed is None:
                    return None
                branches.append((current_cond, parsed[0]))
                current_cond = None
                body_lines = []
                i += 1
                continue
        body_lines.append(lines[i])
        i += 1
    return None


def _parse_block(
    lines: List[str],
    index: int = 0,
    allow_else: bool = False,
    allow_call: bool = False,
    allow_bare_call: bool = False,
    allow_commands: bool = False,
    allow_array_assign: bool = False,
) -> Optional[tuple[List[Statement], int]]:
    statements: List[Statement] = []
    i = index
    n = len(lines)

    while i < n:
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if line.startswith("#"):
            i += 1
            continue

        if line.lower().startswith("print("):
            return None

        for_match = FOR_LOOP_PATTERN.match(line)
        if for_match:
            loop_var = for_match.group(1)
            start_e = for_match.group(2).strip()
            end_e = for_match.group(3).strip()
            step_e = for_match.group(4).strip()
            i += 1
            inner_lines: List[str] = []
            depth = 1
            while i < n and depth > 0:
                inner = lines[i].strip()
                if FOR_LOOP_PATTERN.match(inner):
                    depth += 1
                    inner_lines.append(lines[i])
                elif inner.startswith("endfor "):
                    depth -= 1
                    if depth == 0:
                        if inner != f"endfor {loop_var}":
                            return None
                        i += 1
                        break
                    inner_lines.append(lines[i])
                else:
                    inner_lines.append(lines[i])
                i += 1
            inner = _parse_block(
                inner_lines, 0, allow_else, allow_call, allow_bare_call,
                allow_commands, allow_array_assign,
            )
            if inner is None:
                return None
            statements.append(_make_for_stmt(loop_var, start_e, end_e, step_e, inner[0]))
            continue

        while_match = WHILE_LOOP_PATTERN.match(line)
        if while_match:
            condition = while_match.group(1).strip()
            i += 1
            inner_lines: List[str] = []
            depth = 1
            while i < n and depth > 0:
                inner = lines[i].strip()
                if WHILE_LOOP_PATTERN.match(inner):
                    depth += 1
                if inner == "endwhile":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                if depth > 0:
                    inner_lines.append(lines[i])
                i += 1
            inner = _parse_block(
                inner_lines, 0, allow_else, allow_call, allow_bare_call,
                allow_commands, allow_array_assign,
            )
            if inner is None:
                return None
            statements.append(WhileStmt(condition, inner[0]))
            continue

        if _parse_if_header(line) is not None:
            parsed_if = _parse_if_block(
                lines, i, allow_else, allow_call, allow_bare_call,
                allow_commands, allow_array_assign,
            )
            if parsed_if is None:
                return None
            statements.append(parsed_if[0])
            i = parsed_if[1]
            continue

        if line == "endif":
            return statements, i

        if line.startswith("endfor "):
            return statements, i

        if line == "endwhile":
            return statements, i

        if line.lower() == "break":
            statements.append(BreakStmt())
            i += 1
            continue

        mplot = _parse_mplot(line)
        if mplot is not None:
            statements.append(mplot)
            i += 1
            continue

        plot_stmt = _parse_plot(line)
        if plot_stmt is not None:
            statements.append(plot_stmt)
            i += 1
            continue

        draw_line_stmt = _parse_draw_line(line)
        if draw_line_stmt is not None:
            statements.append(draw_line_stmt)
            i += 1
            continue

        draw_circle_stmt = _parse_draw_circle(line)
        if draw_circle_stmt is not None:
            statements.append(draw_circle_stmt)
            i += 1
            continue

        arr = _parse_array_assign(line)
        if arr is not None:
            if not allow_bare_call and not allow_array_assign:
                return None
            statements.append(arr)
            i += 1
            continue

        assign = _parse_assign(line)
        if assign is not None:
            statements.append(assign)
            i += 1
            continue

        cmd = _parse_command(line, allow_commands)
        if cmd is not None:
            statements.append(cmd)
            i += 1
            continue

        call = _parse_call(line)
        if call is not None:
            if not allow_call:
                return None
            statements.append(call)
            i += 1
            continue

        bare = _parse_bare_call(line, allow_bare_call)
        if bare is not None:
            statements.append(bare)
            i += 1
            continue

        return None

    return statements, i


def try_compile_loop_block(loop_block: List[str]) -> Optional[CompiledBlock]:
    global COMPILED_LOOP_ATTEMPTS, COMPILED_LOOP_HITS, COMPILED_LOOP_FALLBACKS
    if not optimization_flags.ENABLE_COMPILED_LOOPS:
        return None
    COMPILED_LOOP_ATTEMPTS += 1
    if not loop_block:
        return None
    cache_key = tuple(loop_block)
    if cache_key in _LOOP_BODY_CACHE:
        COMPILED_LOOP_HITS += 1
        return _LOOP_BODY_CACHE[cache_key]
    try:
        result = _parse_block(
            loop_block, 0,
            allow_else=True,
            allow_call=True,
            allow_bare_call=False,
            allow_commands=True,
            allow_array_assign=True,
        )
        if result is None:
            COMPILED_LOOP_FALLBACKS += 1
            return None
        statements, _ = result
        body = CompiledBlock(statements)
        _LOOP_BODY_CACHE[cache_key] = body
        COMPILED_LOOP_HITS += 1
        return body
    except Exception:
        COMPILED_LOOP_FALLBACKS += 1
        return None


def try_compile_procedure_block(proc_block: List[str]) -> Optional[CompiledBlock]:
    global COMPILED_PROC_ATTEMPTS, COMPILED_PROC_HITS, COMPILED_PROC_FALLBACKS
    if not optimization_flags.ENABLE_COMPILED_PROCEDURES:
        return None
    COMPILED_PROC_ATTEMPTS += 1
    if not proc_block:
        return None
    cache_key = tuple(proc_block)
    if cache_key in _PROCEDURE_BODY_CACHE:
        COMPILED_PROC_HITS += 1
        return _PROCEDURE_BODY_CACHE[cache_key]
    try:
        result = _parse_block(
            proc_block, 0,
            allow_else=True,
            allow_call=True,
            allow_bare_call=True,
            allow_commands=True,
            allow_array_assign=True,
        )
        if result is None:
            COMPILED_PROC_FALLBACKS += 1
            return None
        statements, _ = result
        body = CompiledBlock(statements)
        _PROCEDURE_BODY_CACHE[cache_key] = body
        COMPILED_PROC_HITS += 1
        return body
    except Exception:
        COMPILED_PROC_FALLBACKS += 1
        return None


def run_compiled_block(compiled: CompiledBlock, ctx: ExecContext) -> None:
    global COMPILED_PROC_CALLS
    COMPILED_PROC_CALLS += 1
    try:
        _run_body(compiled.statements, ctx)
    except LoopBreak:
        pass


def run_compiled_while_body(
    compiled: CompiledBlock,
    condition: str,
    ctx: ExecContext,
) -> None:
    from pixil_utils.shutdown import shutdown_requested

    while True:
        if shutdown_requested() or ctx.is_expired():
            break
        if not ctx.eval_cond(condition):
            break
        try:
            for stmt in compiled.statements:
                stmt.run(ctx)
        except LoopBreak:
            break
        global COMPILED_LOOP_ITERATIONS
        COMPILED_LOOP_ITERATIONS += 1


def run_compiled_loop_body(
    compiled: CompiledBlock,
    loop_var: str,
    start: float,
    end: float,
    step: float,
    ctx: ExecContext,
) -> None:
    from pixil_utils.shutdown import shutdown_requested

    epsilon = 1e-10
    current = start
    while (step > 0 and current <= end + epsilon) or (step < 0 and current >= end - epsilon):
        if shutdown_requested() or ctx.is_expired():
            break
        ctx.variables.set(loop_var, current)
        try:
            for stmt in compiled.statements:
                stmt.run(ctx)
        except LoopBreak:
            break
        global COMPILED_LOOP_ITERATIONS
        COMPILED_LOOP_ITERATIONS += 1
        current += step


def make_loop_context(
    variables: Any,
    mplot_fn: Callable[..., None],
    is_expired: Callable[[], bool],
    call_procedure: Optional[Callable[[str], None]] = None,
    run_command: Optional[Callable[[str, List[str]], None]] = None,
    plot_fn: Optional[Callable[..., None]] = None,
    draw_line_fn: Optional[Callable[..., None]] = None,
    draw_circle_fn: Optional[Callable[..., None]] = None,
) -> ExecContext:
    def eval_expr(expr: str) -> Any:
        return evaluate_math_expression(expr, variables)

    def eval_cond(condition: str) -> bool:
        fast = evaluate_condition_fast(condition, variables)
        if fast is not None:
            return bool(fast)
        return bool(evaluate_condition(condition, variables))

    return ExecContext(
        variables=variables,
        eval_expr=eval_expr,
        eval_cond=eval_cond,
        mplot=mplot_fn,
        is_expired=is_expired,
        call_procedure=call_procedure,
        run_command=run_command,
        plot=plot_fn,
        draw_line=draw_line_fn,
        draw_circle=draw_circle_fn,
    )


class ReusableLoopContext:
    """Lazy-built ExecContext reused across compiled loop/procedure invocations."""

    __slots__ = (
        "_variables", "_mplot_fn", "_is_expired", "_call_procedure", "_run_command",
        "_plot_fn", "_draw_line_fn", "_draw_circle_fn", "_ctx",
    )

    def __init__(
        self,
        variables: Any,
        mplot_fn: Callable[..., None],
        is_expired: Callable[[], bool],
        *,
        call_procedure: Optional[Callable[[str], None]] = None,
        run_command: Optional[Callable[[str, List[str]], None]] = None,
        plot_fn: Optional[Callable[..., None]] = None,
        draw_line_fn: Optional[Callable[..., None]] = None,
        draw_circle_fn: Optional[Callable[..., None]] = None,
    ) -> None:
        self._variables = variables
        self._mplot_fn = mplot_fn
        self._is_expired = is_expired
        self._call_procedure = call_procedure
        self._run_command = run_command
        self._plot_fn = plot_fn
        self._draw_line_fn = draw_line_fn
        self._draw_circle_fn = draw_circle_fn
        self._ctx: Optional[ExecContext] = None

    def get(self) -> ExecContext:
        if self._ctx is None:
            self._ctx = make_loop_context(
                self._variables,
                self._mplot_fn,
                self._is_expired,
                call_procedure=self._call_procedure,
                run_command=self._run_command,
                plot_fn=self._plot_fn,
                draw_line_fn=self._draw_line_fn,
                draw_circle_fn=self._draw_circle_fn,
            )
        return self._ctx

    def reset(self) -> None:
        self._ctx = None
