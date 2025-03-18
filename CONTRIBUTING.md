# Contributing to Pixil

Thank you for your interest in contributing to Pixil! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Enhancements](#suggesting-enhancements)
  - [Your First Code Contribution](#your-first-code-contribution)
  - [Pull Requests](#pull-requests)
- [Styleguides](#styleguides)
  - [Git Commit Messages](#git-commit-messages)
  - [Python Styleguide](#python-styleguide)
  - [Pixil Script Styleguide](#pixil-script-styleguide)
- [Project Structure](#project-structure)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

To get started with development:

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/pixil-led-matrix.git`
3. Set up the development environment (see [INSTALL.md](INSTALL.md))
4. Create a branch for your changes: `git checkout -b my-branch-name`

## How to Contribute

### Reporting Bugs

This section guides you through submitting a bug report. Following these guidelines helps maintainers understand your report and reproduce the issue.

**Before Submitting a Bug Report**

- Check the documentation for solutions to common problems
- Check that your issue hasn't already been reported
- Make sure you can reproduce the problem consistently

**How to Submit a Good Bug Report**

- Use a clear and descriptive title
- Describe the exact steps to reproduce the problem
- Provide specific examples
- Describe the behavior you observed after following the steps
- Explain which behavior you expected to see instead and why
- Include screenshots or animated GIFs if possible
- Include details about your configuration and environment:
  - Which version of Pixil you're using
  - Raspberry Pi model and OS version
  - LED matrix type and configuration

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.

**Before Submitting an Enhancement Suggestion**

- Check that your suggestion hasn't already been proposed
- Check if the feature exists in a recent version

**How to Submit a Good Enhancement Suggestion**

- Use a clear and descriptive title
- Provide a step-by-step description of the suggested enhancement
- Provide specific examples to illustrate the steps
- Describe the current behavior and explain the behavior you'd like to see
- Explain why this enhancement would be useful to most Pixil users

### Your First Code Contribution

Unsure where to begin contributing to Pixil? You can start by looking at these categories:

- **Beginner issues** - issues that should only require a few lines of code
- **Documentation** - improvements to README, INSTALL, or code comments
- **Example scripts** - new demonstration scripts or improvements to existing ones
- **Bug fixes** - addressing reported issues

### Pull Requests

- Fill in the required template
- Do not include issue numbers in the PR title
- Follow the [styleguides](#styleguides)
- Update documentation for any changed functionality
- Include tests when adding new features
- The PR should work against the master branch

## Styleguides

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
- Consider starting the commit message with an applicable emoji:
  - 🎨 `:art:` when improving code structure/format
  - 🐎 `:racehorse:` when improving performance
  - 🚱 `:non-potable_water:` when fixing memory leaks
  - 📝 `:memo:` when writing docs
  - 🐛 `:bug:` when fixing a bug
  - 🔥 `:fire:` when removing code or files

### Python Styleguide

All Python code should adhere to [PEP 8](https://www.python.org/dev/peps/pep-0008/).

Additionally:
- Use 4 spaces for indentation
- Use docstrings for all public functions, classes, and methods
- Use type hints where appropriate
- Maximum line length of 100 characters

### Pixil Script Styleguide

For Pixil scripts:

- Use consistent indentation (2 spaces recommended)
- Use clear, descriptive variable names with v_ prefix
- Group related commands together
- Use comments to explain complex sections
- For complex scripts, use procedures to organize code
- Follow this order for script sections:
  1. Constants and initial variable declarations
  2. Array creation and initialization
  3. Procedure definitions
  4. Main script logic

Example:
```
# Constants and initial variables
v_radius = 5
v_color = "blue"
v_speed = 2

# Array creation
create_array(v_positions, 10)
for v_i in (0, 9, 1) then
    v_positions[v_i] = v_i * 7
endfor v_i

# Procedure definition
def draw_pattern {
    for v_i in (0, 9, 1) then
        draw_circle(v_positions[v_i], 32, v_radius, v_color, 100, true)
    endfor v_i
}

# Main script logic
while v_running == true then
    call draw_pattern
    rest(0.5)
endwhile
```

## Project Structure

Understanding the project's structure will help you contribute effectively:

- **Pixil.py**: Main script interpreter
- **pixil_utils/**: Utility functions for parsing, math operations, and script management
  - Focus on this directory for language feature changes
- **rgb_matrix_lib/**: LED matrix interface and drawing operations
  - Focus on this directory for hardware interaction changes
- **shared/**: Queue system for command execution
  - Focus on this directory for performance improvements
- **scripts/**: Example Pixil scripts
  - Add new examples here

When adding new features, consider which component of the system should be modified.
