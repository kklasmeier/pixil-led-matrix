#!/bin/bash

# Pixil Color Assignment Checker
# Scans all .pix files for color assignments without quotes

echo "Scanning Pixil scripts for unquoted color assignments..."
echo "======================================================="

# Change to the scripts directory
SCRIPT_DIR="/home/pi/Lightshow/git/scripts"
cd "$SCRIPT_DIR" || { echo "Error: Cannot find scripts directory at $SCRIPT_DIR"; exit 1; }

# Define common color names (you can add more as needed)
COLORS=(
    "black" "white" "gray" "light_gray" "dark_gray" "silver"
    "red" "crimson" "maroon" "rose" "pink" "salmon" "coral"
    "brown" "standard_brown" "dark_brown" "wood_brown" "tan"
    "orange" "gold" "peach" "bronze"
    "yellow" "lime" "green" "olive" "spring_green" "forest_green"
    "mint" "teal" "turquoise" "cyan" "sky_blue" "azure"
    "blue" "navy" "royal_blue" "ocean_blue" "indigo"
    "purple" "violet" "magenta" "lavender"
)

# Initialize counters
total_files=0
files_with_issues=0
total_issues=0

# Create regex pattern for unquoted color assignments
# Pattern explanation:
# ^[[:space:]]*v_[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*=[[:space:]]*(color_name)[[:space:]]*$
# - ^[[:space:]]*: start of line with optional whitespace
# - v_[a-zA-Z_][a-zA-Z0-9_]*: variable name starting with v_
# - [[:space:]]*=[[:space:]]*: equals sign with optional whitespace
# - (color_name): the actual color name (not in quotes)
# - [[:space:]]*$: optional whitespace to end of line

echo "Checking for these color names: ${COLORS[*]}"
echo ""

# Find all .pix files recursively
while IFS= read -r -d '' file; do
    ((total_files++))
    
    # Check for each color
    issues_in_file=""
    
    for color in "${COLORS[@]}"; do
        # Look for variable assignments with unquoted color names
        # This regex finds: v_something = colorname (without quotes)
        matches=$(grep -n "^[[:space:]]*v_[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*=[[:space:]]*${color}[[:space:]]*$" "$file" 2>/dev/null)
        
        if [[ -n "$matches" ]]; then
            issues_in_file+="$matches"$'\n'
        fi
    done
    
    if [[ -n "$issues_in_file" ]]; then
        ((files_with_issues++))
        
        # Get relative path for cleaner output
        relative_path="${file#$SCRIPT_DIR/}"
        
        echo "📁 File: $relative_path"
        echo "   Unquoted color assignments found:"
        
        # Process each line with issues
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                ((total_issues++))
                line_num=$(echo "$line" | cut -d: -f1)
                line_content=$(echo "$line" | cut -d: -f2-)
                
                # Extract the color name from the assignment
                color_name=$(echo "$line_content" | sed -n 's/^[[:space:]]*v_[a-zA-Z_][a-zA-Z0-9_]*[[:space:]]*=[[:space:]]*\([a-zA-Z_][a-zA-Z0-9_]*\)[[:space:]]*$/\1/p')
                
                echo "   📍 Line $line_num: $color_name"
                echo "      Current: $(echo "$line_content" | xargs)"
                echo "      Fix to:  $(echo "$line_content" | sed 's/= *'$color_name' */= "'$color_name'"/' | xargs)"
                echo ""
            fi
        done <<< "$issues_in_file"
    fi
    
done < <(find . -name "*.pix" -type f -print0)

echo "======================================================="
echo "📊 SUMMARY:"
echo "   Total .pix files scanned: $total_files"
echo "   Files with unquoted color assignments: $files_with_issues"
echo "   Total unquoted color assignments: $total_issues"

if [[ $total_issues -eq 0 ]]; then
    echo ""
    echo "✅ No issues found! All color assignments use proper quotes."
else
    echo ""
    echo "⚠️  Fix needed: Add quotes around color names in variable assignments"
    echo "   Example: v_color = red → v_color = \"red\""
    echo ""
    echo "💡 Quick fix command for a specific file:"
    echo "   sed -i 's/= *red *$/= \"red\"/' filename.pix"
    echo "   sed -i 's/= *blue *$/= \"blue\"/' filename.pix"
    echo "   (etc. for each color)"
fi

echo ""