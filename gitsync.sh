#!/bin/bash

# Interactive Git script for managing GitHub pushes
# Run from the root of your Git repository

# Ensure we're in a Git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "Error: This directory is not a Git repository. Please navigate to your project root."
    exit 1
fi

echo "=== GitHub Interaction Script ==="
echo "Current directory: $(pwd)"
echo "Repository: $(git remote -v | grep fetch | awk '{print $2}')"
echo "Current branch: $(git branch --show-current)"
echo ""

# Step 1: Show current Git status
echo "=== Checking Git Status ==="
git status
echo ""

# Step 2: Stage changes interactively
echo "=== Staging Changes ==="
read -p "Do you want to stage all changes? (y/n): " stage_all
if [ "$stage_all" = "y" ] || [ "$stage_all" = "Y" ]; then
    echo "Staging all changes..."
    git add .
    echo "Changes staged:"
    git status --short
else
    echo "Enter the files you want to stage (space-separated, e.g., 'file1.py file2.txt'), or press Enter to skip:"
    read -r files_to_stage
    if [ -n "$files_to_stage" ]; then
        echo "Staging: $files_to_stage"
        git add $files_to_stage
        echo "Changes staged:"
        git status --short
    else
        echo "No files staged."
    fi
fi
echo ""

# Step 3: Check if there’s anything to commit
if git diff --cached --quiet; then
    echo "Nothing staged to commit. Exiting."
    exit 0
fi

# Step 4: Commit changes
echo "=== Committing Changes ==="
echo "Current staged changes:"
git diff --cached --name-only
echo ""
read -p "Enter your commit message: " commit_message
if [ -z "$commit_message" ]; then
    echo "Commit message cannot be empty. Using default message."
    commit_message="Update from interactive script"
fi
echo "Committing with message: '$commit_message'"
git commit -m "$commit_message"
echo "Commit complete:"
git log -1 --oneline
echo ""

# Step 5: Push to GitHub
echo "=== Pushing to GitHub ==="
current_branch=$(git branch --show-current)
read -p "Push to 'origin $current_branch'? (y/n): " push_confirm
if [ "$push_confirm" = "y" ] || [ "$push_confirm" = "Y" ]; then
    echo "Pushing to 'origin/$current_branch'..."
    git push origin "$current_branch"
    if [ $? -eq 0 ]; then
        echo "Successfully pushed to GitHub!"
    else
        echo "Push failed. Check your connection or credentials."
        exit 1
    fi
else
    echo "Push skipped. Your changes are committed locally but not on GitHub."
fi
echo ""

# Step 6: Final status check
echo "=== Final Check ==="
read -p "Would you like to see the current Git status? (y/n): " status_confirm
if [ "$status_confirm" = "y" ] || [ "$status_confirm" = "Y" ]; then
    echo "Running 'git status'..."
    git status
else
    echo "Skipping status check."
fi

echo ""
echo "=== Done! ==="
