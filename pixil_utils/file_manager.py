"""
File management utilities for Pixil script interpreter.
Handles script file operations and path management.
"""

import os
from pathlib import Path
from .debug import debug_print, DEBUG_CONCISE, DEBUG_VERBOSE
import os

        
class PixilFileManager:
    def __init__(self, default_script='test_regression_single'):
        # Get the directory where Pixil.py is located (up one level from utils)
        self.root_dir = Path(__file__).parent.parent.absolute()
        self.script_dir = self.root_dir / 'scripts'
        self.default_script = default_script

    def read_file_line_by_line(self, file_path):
        """Generator function to read file line by line."""
        file = None
        try:
            debug_print(f"Starting file operation for: {file_path}", DEBUG_VERBOSE)
            debug_print(f"Current working directory: {os.getcwd()}", DEBUG_VERBOSE)

            # Try to open file first
            file = open(file_path, 'r')
            debug_print(f"Successfully opened file: {file_path}", DEBUG_VERBOSE)

            for line in file:
                try:
                    yield line.strip()
                except GeneratorExit:
                    debug_print(f"Generator exiting early for: {file_path}", DEBUG_VERBOSE)
                    break

        except IOError as e:
            debug_print(f"Error reading file {file_path}: {str(e)}", DEBUG_CONCISE)
            raise
        finally:
            if file:
                debug_print(f"Closing file handle for: {file_path}", DEBUG_VERBOSE)
                file.close()

    def get_script_path(self, script_name=None):
        """
        Resolve full script path from name or use default.
        Handles both direct paths and relative paths including subdirectories.
        
        Args:
            script_name: Optional script name or path
                
        Returns:
            Path: Full path to script file
                
        Raises:
            FileNotFoundError: If script file doesn't exist
        """
        if not script_name:
            script_name = self.default_script

        # Handle both direct and relative paths
        script_path = Path(script_name)
        
        # Try multiple path resolutions in order:
        possible_paths = [
            # 1. Direct absolute path
            script_path,
            # 2. Relative to scripts directory
            self.script_dir / script_path,
            # 3. Relative to scripts directory with .pix extension
            self.script_dir / f"{script_path}.pix"
        ]
        
        # Try each possible path
        for path in possible_paths:
            if path.exists():
                debug_print(f"Found script at: {path}", DEBUG_CONCISE)
                return path
                
        # If we get here, no valid path was found
        raise FileNotFoundError(
            f"Script file '{script_name}' not found.\n"
            f"Tried the following locations:\n"
            f"- {possible_paths[0]}\n"
            f"- {possible_paths[1]}\n"
            f"- {possible_paths[2]}\n"
            f"Scripts should be placed in: {self.script_dir}"
        )



