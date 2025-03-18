# Pixil LED Matrix

A Python-based scripting language for controlling 64x64 LED matrix displays with Raspberry Pi.

## Overview

Pixil is a custom scripting language designed to make creating animations and visualizations on RGB LED matrix displays intuitive and accessible. The language abstracts away the complexities of controlling LED matrices directly, providing simple commands for drawing, animation, and interactive content.

The project uses a producer/consumer architecture with a command queue to manage LED matrix operations, making it efficient for complex animations while maintaining synchronization when needed.

## Features

- **Custom Scripting Language**: Designed specifically for LED matrix control
- **Simple Drawing Commands**: Lines, circles, rectangles, polygons, and single pixels
- **Animation Framework**: Frame control and automatic "burnout" effects
- **Variables and Expressions**: Support for dynamic content with math operations
- **Control Structures**: if/then/else, for loops, while loops
- **Arrays**: Support for numeric and string arrays
- **Math Functions**: Comprehensive set of math operations
- **Sprites**: Create reusable objects that can be instantiated multiple times
- **Text Rendering**: Display text with multiple effects (type, scan, slide, dissolve, wipe)
- **Color Control**: Named colors and intensity customization
- **Procedures**: Define reusable code blocks
- **Performance Controls**: Throttle and sync_queue commands for animation tuning

## Reference
For detailed installation instructions, see [INSTALL.md](docs/INSTALL.md).

For complete language documentation, see [AI_Instructions.txt](docs/AI_Instructions.txt).

## Example Scripts

The project includes over 70 example scripts demonstrating various animations and effects:

- **Visual Effects**: Aurora Borealis, Electric Arcs, Fireworks, Lightning
- **Animations**: Bouncing Ball, Digital Rain, Fireflies, Particle Fountain
- **Simulations**: Boids Flocking, Solar System, Swarm, Gravity Wells
- **Games**: Missile Command, Pong, Snake, Space Invaders
- **Patterns**: Fractals, Spirograph, Kaleidoscope, Lissajous Curves
- **3D Effects**: Wormhole, 3D Perspective, Psychedelic Tunnel

## Installation

### Hardware Requirements

- Raspberry Pi (Model 3 or 4 recommended)
- 64x64 RGB LED Matrix Display
- Appropriate power supply for your matrix

### Software Setup

1. Clone this repository:
   ```
   git clone https://github.com/kklasmeier/pixil-led-matrix.git
   cd pixil-led-matrix
   ```

2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run a sample script:
   ```
   python Pixil.py scripts/examples/bouncing_ball.txt
   ```

## Language Reference

### Drawing Commands

```
draw_line(x1, y1, x2, y2, color, intensity, duration)
plot(x, y, color, intensity, duration)
draw_rectangle(x, y, width, height, color, intensity, filled, duration)
draw_circle(x, y, radius, color, intensity, filled, duration)
clear()
draw_polygon(x, y, radius, sides, color, intensity, rotation, filled, duration)
```

### Variables and Expressions

```
v_x = 10
v_color = "red"
v_result = v_x * 2 + 5
```

### Control Structures

```
if v_x > 10 then
    plot(v_x, v_y, red, 100)
endif

for v_i in (0, 10, 1) then
    draw_circle(v_i * 5, 30, 3, blue, 100, true)
endfor v_i

v_count = 0
while v_count < 5 then
    draw_line(0, v_count * 10, 63, v_count * 10, green, 100)
    v_count = v_count + 1
endwhile
```

### Arrays

```
create_array(v_points, 10)
v_points[0] = 5
v_points[1] = 10

create_array(v_colors, 5, string)
v_colors[0] = "red"
v_colors[1] = "blue"
```

### Sprites

```
define_sprite(ball, 10, 10)
    draw_circle(5, 5, 4, red, 100, true)
endsprite

show_sprite(ball, 20, 30)
move_sprite(ball, 25, 35)
hide_sprite(ball)
```

### Frame Control

```
begin_frame
    draw_circle(32, 32, 20, red, 100, true)
    draw_line(10, 10, 54, 54, yellow, 100)
end_frame
```

### Text Commands

```
draw_text(10, 20, "Hello World", piboto-regular, 12, white, 75, SLIDE, LEFT)
clear_text(10, 20)
```

## Project Structure

- **Pixil.py**: Main script interpreter - Parses and executes Pixil script commands
- **pixil_utils/**: Utility functions for parsing, math operations, and script management
- **rgb_matrix_lib/**: LED matrix interface and drawing operations
- **shared/**: Queue system for command execution
- **scripts/**: Example Pixil scripts demonstrating various animations

## Contributing

Contributions are welcome! Please read the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to submit issues, feature requests, and code.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Special thanks to the [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) library
- Inspired by various LED art projects in the maker community


