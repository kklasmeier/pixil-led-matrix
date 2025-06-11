from multiprocessing import Queue, Process
import time
from typing import Optional
import threading
from queue import Empty, Full

class MatrixCommandQueue:
    """Manages command queue between Pixil and RGB Matrix Library"""
    
    def __init__(self, queue_size: int = 5000):
        """Initialize command queue with specified size"""
        self.command_queue = Queue(maxsize=queue_size)
        self._consumer_process: Optional[Process] = None
        self._running = False
        self.last_command_time = time.time() * 1000  # Convert to milliseconds
        self.throttle_factor = 1.0  # Add throttle factor, default to 1.0 (normal speed)

    def set_pause_callbacks(self, on_pause=None, on_resume=None):
        """Set callbacks for queue pause/resume events."""
        self.on_queue_pause = on_pause
        self.on_queue_resume = on_resume
    
    def reset_throttle(self):
        """Reset throttle factor to default"""
        self.throttle_factor = 1.0
        
    def set_throttle(self, factor: float):
        """Set the throttle factor to control command timing"""
        try:
            factor = float(factor)
            if factor < 0:
                raise ValueError("Throttle factor must be greater than 0")
            self.throttle_factor = factor
        except ValueError as e:
            raise ValueError(f"Invalid throttle factor: {str(e)}")
            
    def start_consumer(self):
        """Start the consumer process"""
        if self._consumer_process is not None:
            raise RuntimeError("Consumer process already running")
            
        self._running = True
        self._consumer_process = Process(
            target=self._consumer_loop,
        )
        self._consumer_process.start()
        
    def stop_consumer(self):
        """Stop the consumer process"""
        if self._consumer_process is None:
            return
            
        # Send special shutdown command with no delay
        self.put_command("__SHUTDOWN__", force_instant=True)
        
        # Wait for process to end with timeout
        self._consumer_process.join(timeout=2.0)  # Give it 2 seconds to shut down
        
        # If it's still running after timeout, terminate it
        if self._consumer_process.is_alive():
            print("Consumer process did not shut down gracefully, forcing termination")
            self._consumer_process.terminate()
            self._consumer_process.join(timeout=1.0)
            
        self._consumer_process = None
        
    def _calculate_delay(self) -> float:
        """
        Calculate delay since last command in milliseconds
        """
        current_time = time.time() * 1000  # Convert to milliseconds
        delay = (current_time - self.last_command_time) * 0.7 * self.throttle_factor
        return max(0, delay)  # Ensure non-negative delay
        
    def put_command(self, command: str, force_instant: bool = False):
        """Add a command to the queue with timing information"""
        BACKOFF_SLEEP = 1  # seconds
        delay = 0 if force_instant else self._calculate_delay()
        command_tuple = (command, delay)
        
        # Try immediately first
        try:
            # print - this is the one
            # print(f"[QUEUE] Adding command: {command} (delay: {delay}ms)")
            self.command_queue.put_nowait(command_tuple)
            self.last_command_time = time.time() * 1000
            return
        except Full:
            # Queue is full, notify metrics
            if hasattr(self, 'on_queue_pause') and callable(self.on_queue_pause):
                self.on_queue_pause()
        
        # Keep trying with backoff
        while True:
            try:
                time.sleep(BACKOFF_SLEEP)
                self.command_queue.put_nowait(command_tuple)
                self.last_command_time = time.time() * 1000
                
                # Successfully added, notify metrics
                if hasattr(self, 'on_queue_resume') and callable(self.on_queue_resume):
                    self.on_queue_resume()
                return
            except Full:
                continue

    def _consumer_loop(self):
        """Main consumer loop that processes commands with timing"""
        try:
            # Initialize RGB matrix in consumer process only
            from rgb_matrix_lib.api import get_api_instance
            api_instance = get_api_instance()
            #print(f"[{datetime.now()}] [QUEUE] Consumer process started with API instance")
            
            while True:
                try:
                    # Get command tuple with timeout
                    command, delay = self.command_queue.get(timeout=0.01)
                    #print(f"[{datetime.now()}] [QUEUE] Consumer got command: {command} (delay: {delay}ms)")
                    
                    # Check for shutdown command
                    if command == "__SHUTDOWN__":
                        print("[QUEUE] Received shutdown command")
                        break
                    
                    # Wait for specified delay
                    if delay > 0:
                        time.sleep(delay / 1000.0)
                        
                    # Execute command
                    #print(f"[{datetime.now()}] [QUEUE] Executing command: {command}")
                    api_instance.execute_command(command)
                    #print(f"[{datetime.now()}] [QUEUE] Finished executing: {command}")
                    
                except Empty:
                    continue
                except Exception as e:
                    #print(f"[{datetime.now()}] [QUEUE] Error processing command: {e}")
                    continue
                    
        finally:
            #print(f"[{datetime.now()}] [QUEUE] Consumer loop ending, cleaning up")
            if api_instance:
                api_instance.cleanup()

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return self.command_queue.empty()
        
    def wait_until_empty(self, timeout: Optional[float] = None) -> bool:
        """
        Wait until queue is empty.
        
        Args:
            timeout: Maximum time to wait in seconds. None means wait forever.
            
        Returns:
            bool: True if queue became empty, False if timeout occurred
        """
        time.sleep(0.1) # Put a short wait here so the queue has enough time to see any new commands added.
        try:
            start_time = time.time()
            while not self.is_empty():
                if timeout is not None and time.time() - start_time > timeout:
                    return False
                time.sleep(0.1)
            return True
        except KeyboardInterrupt:
            return False  # Exit on interrupt

    def wait_for_completion(self, cooldown: float = 1.0):
        """
        Wait for queue to empty and cooldown period to complete.
        Used between scripts and before final shutdown.
        
        Args:
            cooldown: Number of seconds to wait after queue empties
        """
        # Wait for queue to empty
        self.wait_until_empty()
        # Wait cooldown period
        time.sleep(cooldown)
        
    def cleanup(self):
        """Clean up resources"""
        try:
            # Just stop the consumer immediately on interrupt
            self.stop_consumer_force()
        except:
            pass

    def stop_consumer_force(self):
        """Force stop the consumer process without waiting"""
        if self._consumer_process is None:
            return
            
        try:
            # Force terminate the process
            self._consumer_process.terminate()
            # Brief wait for termination
            self._consumer_process.join(timeout=0.5)
            if self._consumer_process.is_alive():
                self._consumer_process.kill()
        except:
            pass
        finally:
            self._consumer_process = None
            self._running = False

class QueueManager:
    """Singleton manager for the command queue"""
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, queue_size: int = 5000) -> MatrixCommandQueue:
        """Get or create the command queue instance"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = MatrixCommandQueue(queue_size)
            return cls._instance
            
    @classmethod
    def cleanup(cls):
        """Clean up the queue instance"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.cleanup()
                cls._instance = None

