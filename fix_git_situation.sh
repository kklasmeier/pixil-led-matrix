#!/usr/bin/env python3
"""
Fix the Git situation after history rewrite
This script will help resolve the diverged Git history
"""

import subprocess
import sys

def run_command(command, check=True):
    """Run a command and return the result"""
    print(f"Running: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=check)
        if result.stdout:
            print(result.stdout)
        if result.stderr and check:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False

def main():
    print("=== Git History Fix Tool ===")
    print("This will resolve the diverged Git history situation")
    print()
    
    # Show current situation
    print("Current situation:")
    run_command("git status", check=False)
    print()
    
    print("Your options:")
    print("1. Force push (RECOMMENDED) - Overwrites GitHub with your cleaned history")
    print("2. Pull and merge - Brings back the nohup.out problem")
    print("3. Reset and start over - Loses your recent changes")
    print()
    
    choice = input("Choose option (1/2/3): ").strip()
    
    if choice == "1":
        print("\n=== Option 1: Force Push (Recommended) ===")
        print("This will overwrite GitHub with your cleaned history.")
        print("The large nohup.out file will be permanently removed.")
        print()
        
        confirm = input("Are you absolutely sure you want to force push? (yes/no): ").strip().lower()
        
        if confirm == "yes":
            print("Force pushing to GitHub...")
            success = run_command("git push --force origin master", check=False)
            
            if success:
                print("✅ SUCCESS! Your cleaned repository is now on GitHub.")
                print("The nohup.out file has been completely removed from history.")
            else:
                print("❌ Force push failed. Let's try a different approach...")
                print("Sometimes GitHub needs a moment. Try running manually:")
                print("git push --force origin master")
        else:
            print("Force push cancelled.")
    
    elif choice == "2":
        print("\n=== Option 2: Pull and Merge ===")
        print("WARNING: This will bring back the nohup.out file and the size problem!")
        print()
        
        confirm = input("Are you sure you want to proceed? (yes/no): ").strip().lower()
        
        if confirm == "yes":
            print("Pulling from GitHub...")
            run_command("git pull origin master --no-rebase", check=False)
            print("You'll need to resolve the nohup.out issue again.")
        else:
            print("Pull cancelled.")
    
    elif choice == "3":
        print("\n=== Option 3: Reset and Start Over ===")
        print("This will reset your local repository to match GitHub exactly.")
        print("You'll lose the cleanup work but can start fresh.")
        print()
        
        confirm = input("Are you sure you want to reset? (yes/no): ").strip().lower()
        
        if confirm == "yes":
            print("Resetting to GitHub state...")
            run_command("git fetch origin")
            run_command("git reset --hard origin/master")
            print("Repository reset. You can now add .gitignore and start over.")
        else:
            print("Reset cancelled.")
    
    else:
        print("Invalid choice. Please run the script again.")
    
    print("\n=== Status After Action ===")
    run_command("git status", check=False)

if __name__ == "__main__":
    main()
