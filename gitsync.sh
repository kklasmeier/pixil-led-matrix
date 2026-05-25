#!/bin/bash
# Interactive Git script for managing GitHub pushes and reverts
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

# Step 2: Choose between sync or revert
echo "=== Choose Action ==="
current_branch=$(git branch --show-current)
read -p "Sync changes to GitHub or Revert to latest from GitHub? (S/r): " action_choice
action_choice=${action_choice:-S}

if [ "$action_choice" = "r" ] || [ "$action_choice" = "R" ]; then
    echo ""
    echo "=== WARNING: DESTRUCTIVE ACTION ==="
    echo "This will:"
    echo "  - PERMANENTLY DELETE all your local changes"
    echo "  - REMOVE all untracked files and directories"
    echo "  - RESET to the latest commit from 'origin/$current_branch'"
    echo ""
    echo "You will LOSE ALL UNCOMMITTED WORK!"
    echo ""
    read -p "Are you absolutely sure you want to proceed? (y/N): " revert_confirm
    revert_confirm=${revert_confirm:-N}
    
    if [ "$revert_confirm" = "y" ] || [ "$revert_confirm" = "Y" ]; then
        echo ""
        echo "=== Reverting to Latest from GitHub ==="
        echo "Discarding all local changes..."
        git reset --hard HEAD
        
        echo "Removing untracked files..."
        git clean -fd
        
        echo "Pulling latest from 'origin/$current_branch'..."
        git pull origin "$current_branch"
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "Successfully reverted to latest from GitHub!"
            echo "Your local repository now matches 'origin/$current_branch'"
        else
            echo ""
            echo "Pull failed. Check your connection or credentials."
            exit 1
        fi
        
        echo ""
        echo "=== Final Status ==="
        git status
        echo ""
        echo "=== Done! ==="
        exit 0
    else
        echo "Revert cancelled. Continuing with sync process..."
        echo ""
    fi
fi

# Continue with original sync process
echo "=== Staging Changes ==="
read -p "Do you want to stage all changes? (Y/n): " stage_all
stage_all=${stage_all:-y}

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

# Check if there's anything to commit
if git diff --cached --quiet; then
    echo "Nothing staged to commit. Exiting."
    exit 0
fi

# Commit changes
echo "=== Committing Changes ==="
echo "Current staged changes:"
git diff --cached --name-only
echo ""

read -p "Commit title: " commit_title
if [ -z "$commit_title" ]; then
    echo "Title cannot be empty. Using default title."
    commit_title="Update from interactive script"
fi

commit_body=""
read -p "Add a commit body/description? (y/N): " add_body
add_body=${add_body:-N}

if [ "$add_body" = "y" ] || [ "$add_body" = "Y" ]; then
    echo "Enter body lines (blank lines within the body are OK)."
    echo "Press Enter twice on an empty line when finished:"
    empty_lines=0
    while IFS= read -r line; do
        if [ -z "$line" ]; then
            empty_lines=$((empty_lines + 1))
            if [ "$empty_lines" -ge 2 ]; then
                break
            fi
            commit_body+=$'\n'
            continue
        fi
        empty_lines=0
        commit_body+="${line}"$'\n'
    done
fi

echo ""
echo "=== Commit Preview ==="
echo "Title: $commit_title"
if [ -n "$commit_body" ]; then
    echo "Body:"
    printf '%s' "$commit_body"
    if [ "${commit_body: -1}" != $'\n' ]; then
        echo ""
    fi
else
    echo "Body: (none)"
fi
echo "========================"
echo ""

read -p "Create this commit? (Y/n): " commit_confirm
commit_confirm=${commit_confirm:-Y}

if [ "$commit_confirm" != "y" ] && [ "$commit_confirm" != "Y" ]; then
    echo "Commit cancelled. Staged changes are unchanged."
    exit 0
fi

if [ -n "$commit_body" ]; then
    git commit -m "$commit_title" -m "$commit_body"
else
    git commit -m "$commit_title"
fi

if [ $? -ne 0 ]; then
    echo "Commit failed."
    exit 1
fi

echo "Commit complete:"
git log -1 --oneline
echo ""

# Push to GitHub
echo "=== Pushing to GitHub ==="
read -p "Push to 'origin $current_branch'? (Y/n): " push_confirm
push_confirm=${push_confirm:-y}

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

# Final status check
echo "=== Final Check ==="
read -p "Would you like to see the current Git status? (Y/n): " status_confirm
status_confirm=${status_confirm:-y}

if [ "$status_confirm" = "y" ] || [ "$status_confirm" = "Y" ]; then
    echo "Running 'git status'..."
    git status
else
    echo "Skipping status check."
fi
echo ""
echo "=== Done! ==="