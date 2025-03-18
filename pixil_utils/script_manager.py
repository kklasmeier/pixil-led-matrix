"""
Script management utilities for Pixil script runner.
Handles script collection, queue management, and randomization.
"""

import random
from pathlib import Path
from .debug import debug_print, DEBUG_CONCISE, DEBUG_SUMMARY, DEBUG_VERBOSE
from .file_manager import PixilFileManager

class ScriptManager:
    """Manages script collection and execution queue."""
    
    def __init__(self, script_path):
        """
        Initialize script manager.
        
        Args:
            script_path: Path to script or directory (can include wildcards)
        """
        debug_print(f"\nInitializing ScriptManager with path: {script_path}", DEBUG_CONCISE)
        self.script_path = script_path
        self.file_manager = PixilFileManager()
        self.scripts = []
        self.is_wildcard = '*' in script_path
        
        # Initial script collection
        self._collect_scripts()
        debug_print(f"After collection, scripts list contains: {self.scripts}", DEBUG_CONCISE)

        
    def _collect_scripts(self):
        """
        Collect all matching scripts based on path.
        Updates self.scripts list.
        """
        path = Path(self.script_path)
        debug_print(f"Collecting scripts for path: {path}", DEBUG_VERBOSE)
        
        try:
            if self.is_wildcard:
                # Try direct path first
                scripts = list(Path().glob(self.script_path))
                debug_print(f"Direct path search found {len(scripts)} scripts", DEBUG_VERBOSE)
                
                # If no scripts found, try under scripts directory
                if not scripts:
                    scripts_dir = self.file_manager.script_dir
                    if str(path).startswith('scripts/'):
                        # If path already includes scripts/, remove it
                        search_path = str(path)[8:]
                    else:
                        search_path = str(path)
                    scripts = list(scripts_dir.glob(search_path))
                    debug_print(f"Scripts dir search found {len(scripts)} scripts", DEBUG_VERBOSE)
                
                # Filter for .pix files
                self.scripts = [
                    str(p) for p in scripts
                    if p.suffix == '.pix' or p.name.endswith('.pix')
                ]
                
                debug_print(f"Found {len(self.scripts)} .pix scripts", DEBUG_CONCISE)
                
                if not self.scripts:
                    raise FileNotFoundError(f"No .pix scripts found matching {self.script_path}")
                    
            else:
                # Single script - use file_manager to resolve path
                debug_print(f"Attempting to resolve single script path", DEBUG_CONCISE)
                try:
                    path = self.file_manager.get_script_path(self.script_path)
                    self.scripts = [str(path)]
                    debug_print(f"Using single script: {path}", DEBUG_CONCISE)
                except FileNotFoundError:
                    # Try as relative path under scripts directory
                    scripts_dir_path = self.file_manager.script_dir / self.script_path
                    if scripts_dir_path.exists() or (scripts_dir_path.with_suffix('.pix')).exists():
                        path = scripts_dir_path if scripts_dir_path.exists() else scripts_dir_path.with_suffix('.pix')
                        self.scripts = [str(path)]
                        debug_print(f"Found script in scripts directory: {path}", DEBUG_CONCISE)
                    else:
                        raise
                
        except Exception as e:
            debug_print(f"Error collecting scripts: {str(e)}", DEBUG_SUMMARY)
            raise
            
    def shuffle_scripts(self):
        """Randomize script order for wildcard mode."""
        if self.is_wildcard and self.scripts:
            random.shuffle(self.scripts)
            debug_print("Scripts reshuffled", DEBUG_VERBOSE)
            
    def get_script_queue(self):
        """
        Get current script queue.
        
        Returns:
            List of script paths, shuffled if in wildcard mode
        """
        if not self.scripts:
            self._collect_scripts()
            
        if self.is_wildcard:
            self.shuffle_scripts()
            
        debug_print(f"\nReturning script queue: {self.scripts}", DEBUG_CONCISE)
        return self.scripts.copy()
        
    def is_single_script(self):
        """Check if managing single script or collection."""
        return not self.is_wildcard
        
    @property
    def script_count(self):
        """Get number of scripts being managed."""
        return len(self.scripts)

# Export symbols
__all__ = ['ScriptManager']