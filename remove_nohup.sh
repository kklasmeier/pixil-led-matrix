#!/bin/bash
# Script to remove nohup.out from Git history completely

echo "=== Cleaning nohup.out from Git History ==="
echo "This will rewrite Git history to completely remove nohup.out"
echo "WARNING: This changes commit hashes and should only be done if you haven't shared this branch with others"
echo ""

# Check if we're in a git repo
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "Error: Not in a Git repository"
    exit 1
fi

# Show current status
echo "Current repository status:"
git log --oneline -5
echo ""

read -p "Do you want to proceed with removing nohup.out from all Git history? (y/N): " confirm
if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Operation cancelled."
    exit 0
fi

echo ""
echo "Step 1: Using git filter-branch to remove nohup.out from all commits..."

# Remove nohup.out from all commits in history
git filter-branch --force --index-filter \
'git rm --cached --ignore-unmatch nohup.out' \
--prune-empty --tag-name-filter cat -- --all

if [ $? -eq 0 ]; then
    echo "✓ Successfully removed nohup.out from Git history"
else
    echo "✗ Failed to remove nohup.out from Git history"
    exit 1
fi

echo ""
echo "Step 2: Cleaning up references..."

# Clean up the backup refs created by filter-branch
rm -rf .git/refs/original/

# Expire all reflog entries
git reflog expire --expire=now --all

# Garbage collect to actually remove the data
git gc --prune=now --aggressive

echo "✓ Git history cleaned"
echo ""

echo "Step 3: Creating .gitignore to prevent future issues..."

# Create or update .gitignore
if [ ! -f .gitignore ]; then
    echo "Creating new .gitignore file..."
    cat > .gitignore << EOF
# Ignore nohup output files
nohup.out

# Python
__pycache__/
*.py[cod]
*.so
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/

# Environment variables
.env
.env.local

# Logs
*.log
logs/

# OS generated files
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
EOF
else
    echo "Adding nohup.out to existing .gitignore..."
    if ! grep -q "nohup.out" .gitignore; then
        echo "" >> .gitignore
        echo "# Ignore nohup output files" >> .gitignore
        echo "nohup.out" >> .gitignore
    fi
fi

# Stage and commit the .gitignore
git add .gitignore
git commit -m "Add .gitignore to prevent tracking nohup.out and other unwanted files"

echo "✓ .gitignore created/updated"
echo ""

echo "Step 4: Current status after cleanup:"
git status
echo ""

echo "Repository size before and after cleanup:"
echo "Note: You should see a significant reduction in repository size"
du -sh .git
echo ""

echo "=== Cleanup Complete ==="
echo ""
echo "Next steps:"
echo "1. Test that everything still works as expected"
echo "2. Force push to GitHub: git push --force-with-lease origin master"
echo ""
echo "WARNING: The --force-with-lease flag will rewrite history on GitHub."
echo "Only do this if you're sure no one else is working on this branch!"
echo ""
read -p "Do you want to force push now? (y/N): " push_confirm

if [ "$push_confirm" = "y" ] || [ "$push_confirm" = "Y" ]; then
    echo "Force pushing to GitHub..."
    git push --force-with-lease origin master
    
    if [ $? -eq 0 ]; then
        echo "✓ Successfully pushed cleaned history to GitHub!"
    else
        echo "✗ Push failed. You may need to run: git push --force origin master"
        echo "  (Use --force only if you're absolutely sure it's safe)"
    fi
else
    echo "Push skipped. Run this when ready:"
    echo "  git push --force-with-lease origin master"
fi

echo ""
echo "=== All Done! ==="

