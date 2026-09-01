# Particle Primitives Initiative

Reusable motion helpers that keep Pixil as a drawing and show-control language, while the expensive “move lots of dots” work runs as generic building blocks.

Scripts still own spawning, colors, scoring, special rules, and drawing. The primitives only change numbers in arrays. They do not draw.

---

## Why this exists

On the Pi, a Pixil loop that visits every particle (and sometimes every other particle or magnet) is often what makes a show stutter. The first kernels handled bounce-and-collide. This initiative adds the next family: **pull, push, spin, and related motion**.

The test is always the same:

1. Is the idea reusable, not one-show-specific?
2. Does Pixil stay in charge of the look and the story?
3. Would a real show get smoother or denser because of it?

---

## What is already in place

### Particle kernels (generic)

| Command | What it does in plain language |
|---|---|
| `particle_integrate` | Move things: add push to speed, move, optional drag, optional speed cap, optional “how far this frame” scale |
| `particle_collide_bounds` | Bounce off a box |
| `particle_collide_circle_bounds` | Stay inside a round drum, optional spinning wall grip |
| `particle_collide_circles` | Balls bounce off each other |
| `particle_collide_static_circles` | Balls bounce off fixed pegs |
| `particle_apply_attractors` | Wells, magnets, explosions: pull or push, optional spin around the well |
| `particle_verlet_integrate` | Move cloth/rope points using current and previous positions |
| `particle_constrain_distances` | Keep linked points near a chosen distance |
| `particle_apply_springs` | Add push/pull forces along an arbitrary list of springs |
| `particle_flock` | Help neighbors avoid crowding, match direction, and stay together |

`particle_apply_attractors` extras that came out of the first shows:

- Positive strength pulls, negative pushes away
- Per-well strength and per-particle “charge”
- Distance falloff: `1` (weaker farther away), `2` (even faster falloff), `-1` (spring-like, stronger when farther)
- Softening so a well does not explode a particle sitting on top of it
- Optional acceleration cap
- Optional **swirl** (sideways spin around a well)

### Shows converted in this pass

The `_v2` files were folded into the normal names:

| Show | What changed | How it felt |
|---|---|---|
| Gravity Wells | Nested well pull → attractors | Clear win |
| Swarm | Order-mode chase → attractors; native move/bounce; no 20 FPS rest | Clear win |
| Magnetic Marbles | Field loop → attractors; field every frame | Better after `sync_queue` was removed (that wait was hiding the gain) |
| Particle Eruption | Floor blast → a pushing well; native gravity/bounce | Modest; drawing circles still dominates |
| Tornado | Ground debris → attractors + swirl; more debris | Little FPS change; funnel is still angle→screen math and drawing |
| Solar System | Not attractors. Perspective rings → four ellipses; drop throttle/rest | Drawing/pacing win, not a gravity-well win |
| Cloth Simulation | Nested string tighten → Verlet + distance constraints | Clear win at the same 6×6 net |
| Spring Network | Per-spring force loop → `particle_apply_springs` | Same look, cheaper force pass |
| Boids Flocking | Nested everyone-vs-everyone → `particle_flock`; wrap world 25% past each panel edge | Clear win: denser flock, smoother motion |

**Lesson:** the primitive only helps when the nested “every speck vs every well” loop is a large share of the frame. Waiting on the queue (`sync_queue`), `rest()`, and `throttle(1)` can make a show look slow even when physics is already cheap. Drawing many circles or converting angles to pixels can dwarf the force math.

---

## Remaining suggestions

These six are the next candidates, in the same plain-spoken form used at the start of this work.

### 1. Flocking (birds / fish that stay in a group)

**Status: done.** `particle_flock` is in the kernel set. `Boids_Flocking_Simulation.pix` now uses it (denser flock, off-panel wrap). Fish Tank is still independent paths unless you later choose to school them.

**What it would do**  
Each creature looks at its neighbors and does three simple things: don’t crowd, match heading, stay near the group. Occasional scatter or “fly toward a target” would still be written in the script.

**Benefit to Pixil**  
Flocking is famous, but it is brutally expensive in a scripting loop because every bird checks every other bird. A shared flocking step is how you get a *flock* on the matrix instead of five lonely dots. Future animal/crowd shows could reuse it without reinventing the rules.

**Who it would help, and how we know**

- **Boids Flocking** — converted. Neighborhood steering is the kernel; events, target chase, trails, and drawing stay in Pixil.
- **Fish Tank** — 10 fish, but they swim on their own paths. Flocking would not rewrite that show unless you *chose* to make them school. Weaker fit today; good for a future tank.

**Value: 8 / 10**  
Huge payoff for one flagship show and a clear path to more life-like crowds. The attractor primitive can only help the optional “fly toward a target” bit; it cannot replace the core flock rules.

---

### 2. Soft cloth / springs (points tied by strings)

**Status: done.** Generic Verlet, distance-link, and spring-force kernels are
in the kernel set. Cloth and Spring Network now use them under the normal names.

**What it would do**  
Imagine a net in the screen plane: knots, and strings between them. Each frame the knots fall a bit (gravity), then the strings tug them back to a comfortable length. Some knots can be pinned (like the top of a hanging sheet). Drawing stays in the script. This is 2D hanging cloth, not a 3D flag whose folds come from depth toward the viewer.

**Benefit to Pixil**  
Cloth and spring toys are limited by “check every string, several times per frame.” A shared string-solver lets a hanging net look like fabric instead of a 6×6 napkin, without turning Pixil into a physics app.

**Who it would help, and how we know**

- **Cloth Simulation** — **6×6 = 36** points, only **2** tighten-up passes. Each pass walks every horizontal link and every vertical link, measures stretch, and slides both ends. That nested grid is the whole simulation. Size is small on purpose.
- **Spring Network** — **8** masses, at most **14** springs. Each frame it zeroes forces, then for every spring computes stretch and pushes both ends. Same “strings between points” idea, just a looser net than cloth.

**Value: 7 / 10**  
Very on-brand with the kernels, and it would visibly upgrade two shows. Fewer scripts than wells; cloth is the poster child. This is **not** attractors — it needs its own primitive (or a pair: verlet step + distance constraints).

---

### 3. Spin in 3D, then flatten to the screen

**What it would do**  
Think of a wire sculpture in space. Each frame you spin it, then squash it onto the 64×64 panel so you can draw lines between the corners. The script would still pick colors and draw the lines. The “spin the corners and figure out where they land on the panel” would be shared.

**Benefit to Pixil**  
Every 3D show currently copies the same “rotate, then squash” recipe. The language stays visual (draw this edge) instead of full of angle math. Bigger win for *future* denser 3D (more corners, more stars) than for today’s cubes, which only have a handful of points.

**Who it would help, and how we know**

- **Rotating Cube** — 8 corners, each frame: scale, spin Y, spin X, then place on screen.
- **3D Shapes** — same pattern for every vertex: spin X, Y, and Z, then perspective squash.
- **3D Asterisk** — 6 spokes × 2 ends; a loop spins each point around X and Y before drawing.
- **Starfield** — 15–35 stars (up to 50). Each frame it moves depth, then does “nearer looks bigger and brighter.” That is flatten-to-screen, not a cube, but the same family.

**Honesty:** a cube with 8 corners is not why the Pi is slow. This is more “stop repeating homework” and “make richer 3D possible” than an instant FPS jump for the cube you already have.

**Value: 7 / 10**  
Strong for cleanliness and future 3D; weaker as a must-have speed fix for current mesh shows.

---

### 4. Bulk polar motion (angle + radius → screen)

**What it would do**  
Many shows do not think in “x speed, y speed.” They think “this thing lives at an angle and a distance from a center.” A shared step would advance those angles/radii and write screen x,y. Drawing stays in Pixil.

**Benefit to Pixil**  
Tornado taught us that attractors do not help a conveyor of polar dust. The expensive part is `sin`/`cos` for every arm segment and every funnel particle, every frame. A polar helper attacks that directly, and would also serve orbits and radar-style toys.

**Who it would help, and how we know**

- **Tornado** — funnel dust is stored as angle + radius; arms are more trig in nested loops. Debris *did* fit attractors; the funnel did not.
- **Solar System** — four planets on circular paths (already cheap; drawing was the bottleneck, now ellipses). Polar still matches the *model*, even if FPS is not the pain.
- **Orbital Wispfield** — 20 wisps with angle, radii, and speed.
- **Radar / Epicycles / Pendulum Wave** — same family: go around a point.

**Value: 6–7 / 10**  
The Tornado experiment is the evidence. Do this if you want that show (and similar ones) to actually get denser, not just cleaner debris.

---

### 5. Follow a wind map (flow field)

**What it would do**  
You paint a coarse “which way is the wind blowing?” map (today an 8×8 grid of directions). Specks look up the cell they are in and drift that way. Spawning, dying, and colors stay in the script.

**Benefit to Pixil**  
This is how you get organic smoke/ink/flow with many specks. Pixil already has a way to *paint* a whole screen from a formula (`field_program`). This would be the missing piece: *movers* riding a small wind map.

**Who it would help, and how we know**

- **Perlin Noise Particle System** — up to **45** particles (arrays sized to 80), plus **64** wind cells (8×8). Every frame each particle looks up its cell and steps. The comment is literally “8×8 grid = 64 vectors.”

Few other main shows are built this way today, so the library value is high for one rich show and for future flow toys, not for half the playlist.

**Value: 6 / 10**  
Excellent for that show and for new flow effects; not a playlist-wide unlock.

---

### 6. Small companions: speed cap and wrap-around

**Speed cap — what it does**  
“Don’t let this thing go faster than X” as a true *speed* limit (the length of the arrow), not one clamp on x and another on y. Swarm and Boids already do this in Pixil. Integrate already has a per-axis cap; a magnitude cap would match how those shows think.

**Wrap around — what it does**  
Leave the right edge, appear on the left (same for top/bottom). Boids already implements wrap by hand in distance checks and in movement. Bounce-off-walls exists; wrap is the other common edge rule.

**Benefit to Pixil**  
Less copy-paste at the edges of motion. Modest speed wins; big consistency wins next to integrate and wall bounce.

**Value: 6 / 10** as a set  
Worth doing once a larger kernel (flock or cloth) needs them, or as a small polish pass. Polar (item 4) is listed separately because Tornado showed it is a real bottleneck, not just vocabulary.

---

## Suggested order from here

| Next | Idea | Why that rank |
|---|---|---|
| 1 | Polar bulk step | Proven by Tornado: attractors were the wrong tool |
| 2 | 3D spin + flatten | Many scripts copy it; today’s meshes are small so speed gain is milder |
| 3 | Wind-map follow | One deep show, great for future flow |
| 4 | Speed cap (magnitude) + wrap | Completes the particle vocabulary |

---

## How to test a new primitive (the working method)

1. Keep the kernel generic: arrays in, arrays out, no drawing, no show rules.
2. Pick one real `scripts/main` show, not a toy.
3. Make a `_v2` (or a branch) and compare on the matrix: queue depth, fluidity, same look.
4. Watch for fake slowness: `sync_queue`, `rest()`, `throttle(1)`.
5. If the bottleneck is drawing or polar trig, do not pretend attractors (or flocking) will fix it.
6. When a `_v2` is clearly better, replace the original name and drop the suffix.

---

## Files to know

| Path | Role |
|---|---|
| `pixil_utils/particle_engine.py` | The math (kernels) |
| `pixil_utils/particle_commands.py` | Pixil names, checks, dispatch |
| `pixil_utils/parameter_types.py` | Command argument lists |
| `pixil_utils/loop_compiler.py` | Allowlist so commands work inside compiled loops |
| `docs/Pixil_Scripting_Guide.txt` section 20 | Author-facing docs |
| `tests/pixil/test_particle_engine.py` | Kernel tests |
| `tests/pixil/test_particle_commands.py` | Script-command tests |

Grid/field programs (`grid_program`, `field_program`) remain the path for full-screen cellular and distance-field pictures. Do not duplicate those as particle kernels.
