#!/bin/bash

# Pixil Random Parameter Checker
# Scans all .pix files for random() calls with decimal precision parameters

echo "Scanning Pixil scripts for random() calls with decimal precision parameters..."
echo "============================================================================"

# Change to the scripts directory
SCRIPT_DIR="/home/pi/Lightshow/git/scripts"
cd "$SCRIPT_DIR" || { echo "Error: Cannot find scripts directory at $SCRIPT_DIR"; exit 1; }

# Initialize counters
total_files=0
files_with_issues=0
total_issues=0

# Find all .pix files recursively
while IFS= read -r -d '' file; do
    ((total_files++))
    
    # Check if file has any random() calls with decimal precision
    # Pattern explanation:
    # random\s*\(.*,.*,\s*[0-9]*\.[0-9]+\s*\)
    # - random\s*\(: "random" followed by optional whitespace and opening parenthesis
    # - .*,.*,: any characters, comma, any characters, comma (first two parameters)
    # - \s*[0-9]*\.[0-9]+\s*: optional whitespace, decimal number, optional whitespace
    # - \): closing parenthesis
    
    issues_in_file=$(grep -n "random\s*([^)]*,[^)]*,\s*[0-9]*\.[0-9]\+\s*)" "$file" 2>/dev/null)
    
    if [[ -n "$issues_in_file" ]]; then
        ((files_with_issues++))
        
        # Get relative path for cleaner output
        relative_path="${file#$SCRIPT_DIR/}"
        
        echo ""
        echo "📁 File: $relative_path"
        echo "   Issues found:"
        
        # Process each line with issues
        while IFS= read -r line; do
            if [[ -n "$line" ]]; then
                ((total_issues++))
                line_num=$(echo "$line" | cut -d: -f1)
                line_content=$(echo "$line" | cut -d: -f2-)
                
                # Extract just the random() call using a more precise regex
                random_call=$(echo "$line_content" | grep -o "random\s*([^)]*,[^)]*,\s*[0-9]*\.[0-9]\+\s*)")
                
                echo "   📍 Line $line_num: $random_call"
                echo "      Full line: $(echo "$line_content" | xargs)"
            fi
        done <<< "$issues_in_file"
    fi
    
done < <(find . -name "*.pix" -type f -print0)

echo ""
echo "============================================================================"
echo "📊 SUMMARY:"
echo "   Total .pix files scanned: $total_files"
echo "   Files with decimal precision issues: $files_with_issues"
echo "   Total random() calls with decimal precision: $total_issues"

if [[ $total_issues -eq 0 ]]; then
    echo ""
    echo "✅ No issues found! All random() calls use integer precision parameters."
else
    echo ""
    echo "⚠️  Fix needed: Change decimal precision values to integers"
    echo "   Example: random(-1, 1, 0.1) → random(-1, 1, 1)"
    echo "   Where the last parameter is the number of decimal places (0=integer, 1=one decimal, etc.)"
fi

echo ""