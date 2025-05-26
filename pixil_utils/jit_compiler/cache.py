"""
JIT expression cache with LRU eviction and performance tracking.
"""
import time
from collections import OrderedDict
from typing import Dict, Any, Optional
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
        
        # Performance tracking
        self._enabled = True
        
    def evaluate(self, expression: str, variables: Dict[str, Any]) -> Optional[float]:
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
        """Compile expression and add to cache with LRU eviction."""
        start_time = time.time()
        
        # Compile expression
        compiled_expr = self.compiler.compile(expression)
        
        compilation_time = time.time() - start_time
        self.stats.compilation_time += compilation_time
        
        # Add to cache with LRU eviction
        if len(self.cache) >= self.max_size:
            # Remove least recently used expression
            self.cache.popitem(last=False)
            
        self.cache[expression] = compiled_expr
        
        return compiled_expr
    
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