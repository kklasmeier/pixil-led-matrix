import multiprocessing as mp
import time
from typing import Optional
import threading
import traceback
from queue import Empty, Full


class ConsumerRecoveryRequired(RuntimeError):
    """The display worker is no longer safe to use; restart the Pixil process."""


class MatrixCommandQueue:
    """Manages command queue between Pixil and RGB Matrix Library"""
    
    def __init__(
        self,
        queue_size: int = 5000,
        queue_full_timeout: float = 300.0,
        consumer_heartbeat_timeout: float = 300.0,
    ):
        """Initialize command queue with specified size"""
        # Forking after Python has created Queue feeder threads can leave those
        # threads attached to pipes whose consumer was killed.  A spawned
        # process begins with a clean interpreter and does not inherit them.
        self._mp_context = mp.get_context("spawn")
        self._queue_size = queue_size
        self._queue_full_timeout = queue_full_timeout
        self._consumer_heartbeat_timeout = consumer_heartbeat_timeout
        self.command_queue = self._mp_context.Queue(maxsize=queue_size)
        # Consumer -> main: buffer fingerprint after __test_snapshot__
        self._test_snapshot_reply = self._mp_context.Queue(maxsize=1)
        self._consumer_process: Optional[mp.Process] = None
        self._running = False
        self.last_command_time = time.time() * 1000  # Convert to milliseconds
        self.throttle_factor = 1.0  # Add throttle factor, default to 1.0 (normal speed)
        self._drain_requested = self._mp_context.Event()
        self._drain_complete = self._mp_context.Event()
        self._drain_swallowed = self._mp_context.Value('i', 0)
        self._reset_complete = self._mp_context.Event()
        self._shutdown_complete = self._mp_context.Event()
        self._force_shutdown = self._mp_context.Event()
        self._consumer_failed = self._mp_context.Event()
        self._consumer_heartbeat = self._mp_context.Value('d', time.monotonic())

    def set_pause_callbacks(self, on_pause=None, on_resume=None):
        """Set callbacks for queue pause/resume events."""
        self.on_queue_pause = on_pause
        self.on_queue_resume = on_resume
    
    def reset_throttle(self):
        """Reset throttle factor to default"""
        self.throttle_factor = 1.0
        
    def set_throttle(self, factor: float):
        """Set the throttle factor to control command timing"""
        from pixil_utils.param_bounds import clamp_throttle

        try:
            self.throttle_factor = clamp_throttle(factor)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid throttle factor: {str(e)}")
            
    def start_consumer(self):
        """Start the consumer process"""
        if self._consumer_process is not None:
            if self._consumer_process.is_alive():
                raise RuntimeError("Consumer process already running")
            self._consumer_process = None
            
        self._running = True
        self._consumer_failed.clear()
        self._consumer_heartbeat.value = time.monotonic()
        self._consumer_process = self._mp_context.Process(
            target=self._consumer_loop,
        )
        self._consumer_process.start()
        
    def discard_pending(self) -> int:
        """Drop unprocessed commands from the producer-side queue."""
        discarded = 0
        while True:
            try:
                self.command_queue.get_nowait()
                discarded += 1
            except Empty:
                break
        return discarded

    def put_command_priority(self, command: str, timeout: float = 2.0) -> None:
        """Enqueue a control command with zero delay; wait for space if the queue is full."""
        from pixil_utils.shutdown import PixilShutdownRequested, shutdown_requested

        command_tuple = (command, 0)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if shutdown_requested():
                raise PixilShutdownRequested()
            try:
                self.command_queue.put_nowait(command_tuple)
                self.last_command_time = time.time() * 1000
                return
            except Full:
                self.discard_pending()
                time.sleep(0.002)
        raise TimeoutError(f"Could not enqueue priority command: {command}")

    def _recreate_command_queue(self) -> None:
        """
        Replace queue IPC objects after the consumer exits.

        Killing the consumer leaves the old pipe/feeder state in the parent;
        a new consumer then sees an empty queue while the producer sees Full.
        """
        self.command_queue = self._mp_context.Queue(maxsize=self._queue_size)
        self._test_snapshot_reply = self._mp_context.Queue(maxsize=1)

    def _consumer_is_healthy(self) -> bool:
        """Return whether the worker is alive and has recently made progress."""
        if self._consumer_process is None or not self._consumer_process.is_alive():
            return False
        if self._consumer_failed.is_set():
            return False
        return (
            time.monotonic() - self._consumer_heartbeat.value
            <= self._consumer_heartbeat_timeout
        )

    def _raise_recovery_required(self, reason: str) -> None:
        print(f"[QUEUE] Fatal: {reason}; restarting Pixil is required", flush=True)
        raise ConsumerRecoveryRequired(reason)

    def _kill_consumer_process(self, timeout: float = 1.0, graceful: bool = False) -> None:
        """Stop the consumer subprocess."""
        if self._consumer_process is None:
            return
        try:
            if self._consumer_process.is_alive():
                if graceful:
                    try:
                        self.command_queue.put_nowait(('__SHUTDOWN__', 0))
                        self._consumer_process.join(timeout=timeout)
                    except Full:
                        self.discard_pending()
                        try:
                            self.command_queue.put_nowait(('__SHUTDOWN__', 0))
                            self._consumer_process.join(timeout=timeout)
                        except Exception:
                            pass
                    except Exception:
                        pass
                if self._consumer_process.is_alive():
                    self._consumer_process.terminate()
                    self._consumer_process.join(timeout=timeout)
                if self._consumer_process.is_alive():
                    self._consumer_process.kill()
                    self._consumer_process.join(timeout=0.5)
        except Exception:
            pass
        finally:
            self._consumer_process = None
            self._running = False

    def request_fast_drain(self, timeout: float = 3.0) -> int:
        """
        Ask the consumer to swallow pending commands without executing them.

        Returns:
            Number of commands swallowed, or -1 if the consumer did not finish in time.
        """
        if self._consumer_process is None or not self._consumer_process.is_alive():
            return 0

        self._drain_complete.clear()
        self._drain_swallowed.value = 0
        self._drain_requested.set()
        try:
            self.put_command_priority('__DRAIN__')
        except Exception:
            self._drain_requested.clear()
            return -1

        if not self._drain_complete.wait(timeout=timeout):
            self._drain_requested.clear()
            return -1
        self._drain_requested.clear()
        return self._drain_swallowed.value

    def _sleep_delay_interruptible(self, delay_ms: float) -> bool:
        """Sleep for delay_ms; return True if drain or shutdown was requested."""
        if delay_ms <= 0:
            return self._drain_requested.is_set() or self._force_shutdown.is_set()
        end = time.perf_counter() + (delay_ms / 1000.0)
        while True:
            remaining = end - time.perf_counter()
            if remaining <= 0:
                break
            if self._drain_requested.is_set() or self._force_shutdown.is_set():
                return True
            time.sleep(min(0.001, remaining))
        return self._drain_requested.is_set() or self._force_shutdown.is_set()

    def _consumer_blackout_and_exit(self, api_instance) -> None:
        """Black out the matrix and signal shutdown completion to the main process."""
        try:
            api_instance.blackout_display()
        except Exception as blackout_err:
            print(
                f"[QUEUE] Blackout error: {blackout_err}",
                flush=True,
            )
        self._shutdown_complete.set()

    def _apply_script_reset(self, api_instance) -> None:
        """Reset matrix state between scripts (consumer process only)."""
        api_instance.reset_fps()
        if api_instance.frame_mode:
            try:
                api_instance.end_frame()
            except Exception:
                api_instance.frame_mode = False
                api_instance.preserve_frame_changes = False
        api_instance.clear()
        api_instance.dispose_all_sprites()

    def _wait_for_script_reset(self, timeout: float = 3.0) -> bool:
        """Block until the consumer finishes an atomic script reset."""
        self._reset_complete.clear()
        try:
            self.put_command_priority('__SCRIPT_RESET__', timeout=min(timeout, 2.0))
        except TimeoutError:
            return False
        return self._reset_complete.wait(timeout=timeout)

    def _complete_fast_drain(self) -> None:
        """Acknowledge the FIFO drain marker after all older commands were seen."""
        self._drain_requested.clear()
        self._drain_complete.set()

    def _handle_fast_drain_command(self, command: str) -> bool:
        """Discard data during a drain; complete only at the FIFO fence."""
        if command == "__DRAIN__":
            self._complete_fast_drain()
            return True
        if self._drain_requested.is_set():
            self._drain_swallowed.value += 1
            return True
        return False

    def prepare_for_next_script(self, timeout: float = 3.0) -> None:
        """
        Prepare the display for the next script without restarting the consumer.

        Drops producer-side backlog, fast-drains the consumer queue, then runs
        real reset commands on the matrix.
        """
        if self._consumer_process is None or not self._consumer_process.is_alive():
            self.last_command_time = time.time() * 1000
            self.start_consumer()

        self.discard_pending()
        swallowed = self.request_fast_drain(timeout=timeout)
        if swallowed < 0:
            print("[QUEUE] Warning: fast drain timed out; restarting consumer")
            self.reset_for_next_script(timeout=timeout)
            return

        self.last_command_time = time.time() * 1000
        if not self._wait_for_script_reset(timeout=timeout):
            self._raise_recovery_required(
                "script reset was not acknowledged by the display consumer"
            )

    def reset_for_next_script(self, timeout: float = 3.0) -> None:
        """
        Legacy recovery entry point.

        Replacing only the consumer is unsafe: a Queue feeder thread in this
        process can remain blocked on the old consumer pipe forever.  The
        supervisor must restart the entire Pixil process instead.
        """
        self._raise_recovery_required("display consumer recovery was requested")

    def script_transition_cleanup(self, cooldown: float = 0.3) -> None:
        """Discard backlog and reset display for the next script."""
        self.prepare_for_next_script()
        time.sleep(cooldown)

    def _run_emergency_blackout(self, timeout: float = 4.0) -> None:
        from rgb_matrix_lib.emergency_blackout import spawn_emergency_blackout

        spawn_emergency_blackout(timeout=timeout)

    def shutdown_display(self, timeout: float = 5.0) -> None:
        """
        Clear the LED matrix and stop the consumer (Ctrl+C / final exit).

        Sets a force-shutdown flag the consumer polls immediately (does not
        require queue space). If the consumer does not black out in time it is
        killed and a fresh process clears the panel.
        """
        if self._consumer_process is None:
            self._run_emergency_blackout()
            return

        self._force_shutdown.set()
        self._drain_requested.clear()
        self._shutdown_complete.clear()
        self.discard_pending()

        blackout_ok = False
        if self._consumer_process.is_alive():
            blackout_ok = self._shutdown_complete.wait(timeout=timeout)
            self._consumer_process.join(timeout=1.0)

        if self._consumer_process is not None and self._consumer_process.is_alive():
            self._kill_consumer_process(timeout=1.0, graceful=False)
            blackout_ok = False

        self._force_shutdown.clear()

        if not blackout_ok:
            time.sleep(0.25)
            self._run_emergency_blackout(timeout=timeout)

        self._recreate_command_queue()
        self._consumer_process = None
        self._running = False

    def stop_consumer_graceful(self, timeout: float = 4.0) -> None:
        """Clear display and stop the consumer process."""
        self.shutdown_display(timeout=timeout)

    def stop_consumer(self):
        """Stop the consumer process"""
        self.stop_consumer_graceful()
        
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
            #print(f"[QUEUE] Adding command: {command} (delay: {delay}ms)")
            self.command_queue.put_nowait(command_tuple)
            self.last_command_time = time.time() * 1000
            return
        except Full:
            # Queue is full, notify metrics
            if hasattr(self, 'on_queue_pause') and callable(self.on_queue_pause):
                self.on_queue_pause()
        
        # Keep trying with backoff
        from pixil_utils.shutdown import PixilShutdownRequested, shutdown_requested

        deadline = time.monotonic() + self._queue_full_timeout
        while time.monotonic() < deadline:
            if shutdown_requested():
                raise PixilShutdownRequested()
            if not self._consumer_is_healthy():
                self._raise_recovery_required(
                    "display consumer stopped making progress while the command queue was full"
                )
            try:
                time.sleep(min(BACKOFF_SLEEP, max(0, deadline - time.monotonic())))
                self.command_queue.put_nowait(command_tuple)
                self.last_command_time = time.time() * 1000

                # Successfully added, notify metrics
                if hasattr(self, 'on_queue_resume') and callable(self.on_queue_resume):
                    self.on_queue_resume()
                return
            except Full:
                continue
        self._raise_recovery_required(
            f"command queue remained full for {self._queue_full_timeout:.1f} seconds"
        )

    def _consumer_loop(self):
        """Main consumer loop that processes commands with timing"""
        api_instance = None
        try:
            # Initialize RGB matrix in consumer process only
            from rgb_matrix_lib.api import get_api_instance
            api_instance = get_api_instance()
            api_instance.set_drain_checker(self._drain_requested.is_set)
            api_instance.set_shutdown_checker(self._force_shutdown.is_set)

            while True:
                if self._force_shutdown.is_set():
                    self._consumer_blackout_and_exit(api_instance)
                    break

                try:
                    # Get command tuple with timeout
                    command, delay = self.command_queue.get(timeout=0.01)

                    if self._force_shutdown.is_set():
                        self._consumer_blackout_and_exit(api_instance)
                        break

                    # Legacy queue-based shutdown (still honoured if enqueued)
                    if command == "__SHUTDOWN__":
                        self._consumer_blackout_and_exit(api_instance)
                        break

                    if command == "__SCRIPT_RESET__":
                        self._apply_script_reset(api_instance)
                        self._reset_complete.set()
                        continue

                    # __DRAIN__ is a FIFO fence.  While a drain is requested,
                    # discard ordinary commands one at a time.  Acknowledge
                    # only after the marker itself arrives, proving that every
                    # command enqueued before it has been seen.  Draining with
                    # get_nowait() can observe a transient Empty while the
                    # Queue feeder still holds older commands.
                    if self._handle_fast_drain_command(command):
                        continue

                    # Test harness: capture drawing buffer fingerprint (consumer process)
                    if command == "__test_snapshot__":
                        try:
                            from rgb_matrix_lib.test_inspect import emit_test_snapshot

                            fp = emit_test_snapshot(api_instance)
                            try:
                                self._test_snapshot_reply.put_nowait(fp)
                            except Full:
                                try:
                                    self._test_snapshot_reply.get_nowait()
                                except Empty:
                                    pass
                                self._test_snapshot_reply.put_nowait(fp)
                        except Exception as snap_err:
                            print(
                                f"PIXIL_TEST_SNAPSHOT_ERROR={snap_err}",
                                flush=True,
                            )
                        continue

                    # Wait for specified delay (interruptible when drain/shutdown requested)
                    if delay > 0:
                        if self._sleep_delay_interruptible(delay):
                            if self._force_shutdown.is_set():
                                self._consumer_blackout_and_exit(api_instance)
                                break
                            self._drain_swallowed.value += 1
                            continue

                    if self._drain_requested.is_set():
                        self._drain_swallowed.value += 1
                        continue

                    api_instance.execute_command(command)
                    self._consumer_heartbeat.value = time.monotonic()

                except Empty:
                    if self._force_shutdown.is_set():
                        self._consumer_blackout_and_exit(api_instance)
                        break
                    if self._drain_requested.is_set():
                        # Wait for the FIFO marker; Empty may only mean the
                        # producer's feeder thread has not published it yet.
                        continue
                    try:
                        if not api_instance.drain_abort_requested():
                            api_instance.pump_fade_display()
                        self._consumer_heartbeat.value = time.monotonic()
                    except AttributeError:
                        pass
                    continue
                except Exception:
                    self._consumer_failed.set()
                    print(
                        "[QUEUE] Consumer command failed; terminating worker:\n"
                        + traceback.format_exc(),
                        flush=True,
                    )
                    break

        finally:
            if api_instance is not None:
                api_instance.set_drain_checker(None)
                api_instance.set_shutdown_checker(None)
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
        # multiprocessing.Queue hands data to a feeder thread asynchronously.
        # A brief yield lets that thread publish a just-enqueued command without
        # imposing the old 100 ms minimum latency on every frame sync.
        time.sleep(0.002)
        try:
            start_time = time.time()
            from pixil_utils.shutdown import shutdown_requested

            while not self.is_empty():
                if shutdown_requested():
                    return False
                if not self._consumer_is_healthy():
                    self._raise_recovery_required(
                        "display consumer stopped making progress while draining commands"
                    )
                if timeout is not None and time.time() - start_time > timeout:
                    return False
                time.sleep(0.002)
            return True
        except KeyboardInterrupt:
            return False  # Exit on interrupt

    def drain_test_snapshot_reply(self) -> None:
        """Discard stale fingerprint from a prior snapshot in this process."""
        while True:
            try:
                self._test_snapshot_reply.get_nowait()
            except Empty:
                break

    def wait_for_test_snapshot(self, timeout: float = 3.0) -> Optional[str]:
        """Block until consumer posts a buffer fingerprint (or timeout)."""
        try:
            return self._test_snapshot_reply.get(timeout=timeout)
        except Empty:
            return None

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
            self.stop_consumer_graceful()
        except Exception:
            try:
                self.stop_consumer_force()
            except Exception:
                pass

    def stop_consumer_force(self):
        """Force stop the consumer process without waiting"""
        self._kill_consumer_process(timeout=0.5)

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

