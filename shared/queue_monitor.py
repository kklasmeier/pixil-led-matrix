from threading import Thread
import sys
import os
import time
import atexit

class QueueMonitor:
    def __init__(self, queue_instance):
        self.queue_instance = queue_instance
        self.running = False
        self.thread = None
        atexit.register(self.cleanup)
        
    def start(self):
        """Start queue monitoring thread"""
        self.running = True
        self.thread = Thread(target=self._monitor_loop, daemon=True)
        sys.stdout.write('\n\033[s\033[?25l')  # Save cursor position and hide it
        self.thread.start()
        
    def stop(self):
        """Stop monitoring and restore cursor"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        self.cleanup()
            
    def cleanup(self):
        """Restore cursor and position"""
        sys.stdout.write('\033[?25h\033[u\n')  # Show cursor, restore position, and add newline
        sys.stdout.flush()
        
    def _monitor_loop(self):
        """Update queue depth display"""
        while self.running:
            try:
                # Get terminal size
                rows, columns = os.popen('stty size', 'r').read().split()
                rows, columns = int(rows), int(columns)
                
                # Get queue size
                queue_size = self.queue_instance.command_queue.qsize()
                display_text = f"Queue: {queue_size:5d}"
                
                # Position at bottom right
                x = max(0, columns - len(display_text))
                
                # Save current cursor position, move to bottom, write queue size, 
                # and restore cursor position
                sys.stdout.write(f'\033[s\033[{rows};{x}H{display_text}\033[u')
                sys.stdout.flush()
                
            except:
                pass  # Ignore any errors during display
                
            time.sleep(0.1)  # Update 10 times/second