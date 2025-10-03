"""
JIT expression cache with LRU eviction and performance tracking.
"""
import time
from collections import OrderedDict
from typing import Dict, Any, Optional, Union
from ..variable_registry import VariableRegistry
from .compiler import ExpressionCompiler
from .vm import PixilVM, PixilVMError
from .bytecode import CompiledExpression

class JITCacheStats:
    """Performance statistics for JIT cache."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset all statistics."""
        self.cache_attempts = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.compilation_time = 0.0
        self.execution_time = 0.0
        self.total_time_saved = 0.0
        
        # Cache management statistics
        self.evictions = 0              # How many expressions were evicted
        self.recompilations = 0         # How many expressions were recompiled after eviction
        self.max_cache_size_reached = 0 # How many times we hit max cache size

        
    @property
    def hit_rate(self) -> float:
        """Cache hit rate percentage."""
        if self.cache_attempts == 0:
            return 0.0
        return (self.cache_hits / self.cache_attempts) * 100
    
    @property 
    def miss_rate(self) -> float:
        """Cache miss rate percentage."""
        return 100.0 - self.hit_rate

    # Cache utilization properties
    @property
    def eviction_rate(self) -> float:
        """Percentage of compilations that caused evictions."""
        if self.cache_misses == 0:
            return 0.0
        return (self.evictions / self.cache_misses) * 100

class JITExpressionCache:
    """
    JIT compilation cache with LRU eviction.
    
    Compiles expressions on first use and caches the bytecode.
    Subsequent uses execute cached bytecode directly.
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CompiledExpression] = OrderedDict()
        self.compiler = ExpressionCompiler()
        self.vm = PixilVM()
        self.stats = JITCacheStats()
        
        # NEW: Track expression usage for eviction analysis
        self._expression_recompile_tracker = set()  # Track recompiled expressions
        self._enabled = True
        
    def evaluate(self, expression: str, variables: Union[Dict[str, Any], VariableRegistry]) -> Optional[float]:
        """
        Evaluate expression using JIT compilation.
        
        Args:
            expression: Mathematical expression string
            variables: Current variable values
            
        Returns:
            Result of expression evaluation, or None if compilation failed
        """
        if not self._enabled:
            return None
            
        self.stats.cache_attempts += 1
        
        try:
            # Check cache first
            if expression in self.cache:
                self.stats.cache_hits += 1
                compiled_expr = self.cache[expression]
                # Move to end (LRU)
                self.cache.move_to_end(expression)
            else:
                # Cache miss - compile and cache
                self.stats.cache_misses += 1
                compiled_expr = self._compile_and_cache(expression)
                
            # Execute
            start_time = time.time()
            result = self.vm.execute(compiled_expr, variables)
            execution_time = time.time() - start_time
            
            self.stats.execution_time += execution_time
            
            # Estimate time saved vs eval() (rough estimate)
            estimated_eval_time = len(expression) * 0.00001  # Very rough heuristic
            if execution_time < estimated_eval_time:
                self.stats.total_time_saved += (estimated_eval_time - execution_time)
            
            return result
            
        except (ValueError, PixilVMError) as e:
            # Compilation or execution failed - return None to fall back to eval()
            return None
        except Exception as e:
            # Unexpected error - disable JIT and fall back
            self._enabled = False
            return None
    
    def _compile_and_cache(self, expression: str) -> CompiledExpression:
        """Compile expression and add to cache with enhanced LRU eviction tracking."""
        start_time = time.time()
        
        # Check if this expression was previously evicted and is being recompiled
        if expression in self._expression_recompile_tracker:
            self.stats.recompilations += 1
            self._expression_recompile_tracker.discard(expression)  # Remove from tracker
        
        # Compile expression
        compiled_expr = self.compiler.compile(expression)
        
        compilation_time = time.time() - start_time
        self.stats.compilation_time += compilation_time
        
        # Add to cache with enhanced LRU eviction tracking
        if len(self.cache) >= self.max_size:
            # Track eviction statistics
            self.stats.evictions += 1
            self.stats.max_cache_size_reached += 1
            
            # Track the evicted expression for potential recompilation detection
            evicted_expr, _ = self.cache.popitem(last=False)
            self._expression_recompile_tracker.add(evicted_expr)
            
        self.cache[expression] = compiled_expr
        return compiled_expr

    def get_cache_utilization(self) -> dict:
        """Get detailed cache utilization information."""
        return {
            'current_size': len(self.cache),
            'max_size': self.max_size,
            'utilization_percent': (len(self.cache) / self.max_size) * 100,
            'available_slots': self.max_size - len(self.cache),
            'is_full': len(self.cache) >= self.max_size,
            'evictions': self.stats.evictions,
            'recompilations': self.stats.recompilations,
            'eviction_rate': self.stats.eviction_rate,
        }

    def get_top_expressions(self, count: int = 10) -> list:
        """Get the most recently used expressions (top of cache)."""
        if count > len(self.cache):
            count = len(self.cache)
        
        # Get last N items from OrderedDict (most recently used)
        recent_expressions = list(self.cache.keys())[-count:]
        return recent_expressions

    def get_cache_efficiency_report(self) -> str:
        """Generate a detailed cache efficiency report."""
        util = self.get_cache_utilization()
        
        report = [
            "=== JIT Cache Efficiency Report ===",
            f"Cache Size: {util['current_size']}/{util['max_size']} ({util['utilization_percent']:.1f}% full)",
            f"Available Slots: {util['available_slots']}",
            f"Cache Status: {'FULL' if util['is_full'] else 'Available'}",
            "",
            f"Eviction Statistics:",
            f"  Total Evictions: {util['evictions']:,}",
            f"  Recompilations: {util['recompilations']:,}",
            f"  Eviction Rate: {util['eviction_rate']:.1f}% of cache misses",
            "",
            f"Performance Impact:",
            f"  Hit Rate: {self.stats.hit_rate:.1f}%",
            f"  Total Time Saved: {self.stats.total_time_saved:.4f}s",
            f"  Compilation Time: {self.stats.compilation_time:.4f}s",
        ]
        
        if util['recompilations'] > 0:
            efficiency_loss = (util['recompilations'] / self.stats.cache_misses) * 100
            report.extend([
                "",
                f"⚠️  Cache Thrashing Detection:",
                f"  {util['recompilations']:,} expressions recompiled after eviction",
                f"  {efficiency_loss:.1f}% efficiency loss due to cache pressure",
                f"  Consider increasing cache size if this is > 5%"
            ])
        
        return "\n".join(report)

    def get_stats(self) -> JITCacheStats:
        """Get current performance statistics."""
        return self.stats
    
    def clear_cache(self):
        """Clear compilation cache."""
        self.cache.clear()
        
    def disable(self):
        """Disable JIT compilation (fall back to eval)."""
        self._enabled = False
        
    def enable(self):
        """Enable JIT compilation."""
        self._enabled = True
        
    @property
    def cache_size(self) -> int:
        """Current number of cached expressions."""
        return len(self.cache)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'enabled': self._enabled,
            'expressions': list(self.cache.keys()) if len(self.cache) < 20 else f"{len(self.cache)} expressions"
        }