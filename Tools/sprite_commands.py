def generate_sprite_layer(layer_num, sprite_size, spacing, brightness):
    """
    Generate plot commands for a single sprite layer
    
    Args:
        layer_num: Layer number (1-6)
        sprite_size: Size of sprite (width/height)
        spacing: Spacing between dots
        brightness: Brightness value for this layer
    """
    commands = []
    
    # Start sprite definition
    commands.append(f"# Layer {layer_num} ({spacing} pixel spacing)")
    commands.append(f"define_sprite(layer{layer_num}, {sprite_size}, {sprite_size})")
    
    # Generate plot commands for each point
    for y in range(0, sprite_size, spacing):
        for x in range(0, sprite_size, spacing):
            commands.append(f"    plot({x}, {y}, white:{brightness})")
    
    commands.append("endsprite")
    commands.append("")  # Empty line for readability
    return commands

def generate_all_layers():
    """Generate commands for all sprite layers"""
    # Layer configurations: (spacing, brightness)
    layers = [
        (8, 90),   # Layer 1 - closest
        (12, 75),  # Layer 2
        (16, 60),  # Layer 3
        (20, 45),  # Layer 4
        (24, 30),  # Layer 5
        (28, 15)   # Layer 6 - farthest
    ]
    
    sprite_size = 128  # 128x128 sprites
    all_commands = []
    
    for i, (spacing, brightness) in enumerate(layers, 1):
        layer_commands = generate_sprite_layer(i, sprite_size, spacing, brightness)
        all_commands.extend(layer_commands)
    
    return all_commands

def main():
    commands = generate_all_layers()
    
    # Print to console
    print("# 3D Dot Matrix Sprite Definitions")
    print("# Generated Plot Commands\n")
    for cmd in commands:
        print(cmd)
    
    # Optionally save to file
    with open("sprite_commands.txt", "w") as f:
        for cmd in commands:
            f.write(cmd + "\n")

if __name__ == "__main__":
    main()