"""
Pixil Optimization Control Flags

This module contains all optimization flags that can be imported cleanly
by any other module without circular dependencies.

Modify these flags to enable/disable specific optimizations for performance testing.
"""

# REPORT FIELD TO OPTIMIZATION FLAG MAPPING
# This shows which report columns correspond to which optimization flags

"""
OPTIMIZATION FLAGS → REPORT FIELDS MAPPING:

1. ENABLE_PHASE1_FAST_PATH → FP% (Fast Path hit rate)
   - Report Field: FP%
   - Description: Simple variable lookups (v_variable only)
   - Typical Range: 0% or 100%
   - Code Location: Phase 1 Fast Path in parse_value()

2. ENABLE_FAST_MATH → FM% (Fast Math hit rate)  
   - Report Field: FM%
   - Description: Optimized math expressions (try_fast_number, try_fast_arithmetic, etc.)
   - Typical Range: 0%, 57-63%
   - Code Location: Phase 2 optimization in evaluate_math_expression()

3. ENABLE_EXPRESSION_CACHE → C% (Expression Cache hit rate)
   - Report Field: C%
   - Description: Cache results of math expressions
   - Typical Range: 0%, 17-30%
   - Code Location: Expression result caching in evaluate_math_expression()

4. ENABLE_ULTRA_FAST_PATH + ENABLE_FAST_PATH + ENABLE_PARSE_VALUE_CACHE → PV% (Parse Value hit rate)
   - Report Field: PV%
   - Description: Combined parameter parsing optimizations
   - Components:
     * ENABLE_ULTRA_FAST_PATH: Direct integer/color/string detection
     * ENABLE_FAST_PATH: Simple array access and arithmetic
     * ENABLE_PARSE_VALUE_CACHE: LRU cache for parse_value results
   - Typical Range: 0%, 11-12% (low), 77-78% (high)
   - Code Location: Multiple optimizations in parse_value()

5. ENABLE_JIT → JIT% (JIT compilation hit rate)
   - Report Field: JIT%
   - Description: JIT compilation of expressions using compiled bytecode
   - Typical Range: 0%, 100%
   - Code Location: try_jit_compilation() in evaluate_math_expression()

6. ENABLE_JIT → Skip% (JIT skip efficiency)
   - Report Field: Skip%
   - Description: Expressions avoided due to known JIT compilation failures
   - Typical Range: 0%, 61-70%
   - Code Location: JIT line cache skips system

7. ENABLE_JIT → JIT-Size (Number of expressions in JIT cache)
   - Report Field: JIT-Size
   - Description: Count of successfully compiled expressions in cache
   - Typical Range: 0, 54-500
   - Code Location: JIT cache size tracking

8. ENABLE_JIT → JIT-Hit (JIT cache utilization percentage)
   - Report Field: JIT-Hit
   - Description: How full the JIT cache is (percentage of max capacity)
   - Typical Range: 0%, 11-100%
   - Code Location: JIT cache utilization calculation

9. ENABLE_JIT → JIT-Comp (JIT compilation time)
   - Report Field: JIT-Comp
   - Description: Total time spent compiling expressions to bytecode
   - Typical Range: 0.000s, 0.006s-0.209s
   - Code Location: JIT compilation timing

10. ENABLE_JIT → Failed (Failed compilation count)
    - Report Field: Failed
    - Description: Number of unique script lines that failed JIT compilation
    - Typical Range: 0, 36-1038
    - Code Location: Failed script lines tracking

# QUICK REFERENCE FOR TESTING:

# To get FP% = 100%, FM% = 0%, C% = 0%, PV% = 0%, JIT% = 0%:
ENABLE_PHASE1_FAST_PATH = True
ENABLE_FAST_MATH = False
ENABLE_EXPRESSION_CACHE = False
ENABLE_ULTRA_FAST_PATH = False
ENABLE_FAST_PATH = False
ENABLE_PARSE_VALUE_CACHE = False
ENABLE_JIT = False

# To get FP% = 100%, FM% = 59%, C% = 0%, PV% = 0%, JIT% = 0%:
ENABLE_PHASE1_FAST_PATH = True
ENABLE_FAST_MATH = True
ENABLE_EXPRESSION_CACHE = False
ENABLE_ULTRA_FAST_PATH = False
ENABLE_FAST_PATH = False
ENABLE_PARSE_VALUE_CACHE = False
ENABLE_JIT = False

# To get all zeros (baseline):
ENABLE_PHASE1_FAST_PATH = False
ENABLE_FAST_MATH = False
ENABLE_EXPRESSION_CACHE = False
ENABLE_ULTRA_FAST_PATH = False
ENABLE_FAST_PATH = False
ENABLE_PARSE_VALUE_CACHE = False
ENABLE_JIT = False

# IMPORTANT NOTES:

# 1. PV% is a COMPOSITE metric
#    - It combines three different optimization flags
#    - You can't control PV% independently - it's the sum of all parse value optimizations
#    - High PV% (77-78%) = all three parse value flags enabled
#    - Low PV% (11-12%) = some parse value flags enabled
#    - Zero PV% (0%) = all parse value flags disabled

# 2. JIT metrics are all related
#    - JIT%, Skip%, JIT-Size, JIT-Hit, JIT-Comp, Failed all come from ENABLE_JIT
#    - They're either all active or all zero

# 3. Performance correlation
#    - FP% = 100% → Usually +14-17 cmds/s
#    - FM% = 59% → Usually +3-7 cmds/s (when combined with FP)
#    - C% = 27% → Variable impact, often neutral or slightly negative
#    - PV% = 77% → Usually NEGATIVE impact on performance
#    - JIT% = 100% → Usually NEGATIVE impact due to compilation overhead

# TESTING STRATEGY:
# Start with all flags False (get all zeros in report)
# Then enable flags one by one to see individual impact:
# 1. Enable ENABLE_PHASE1_FAST_PATH → See FP% change to 100%
# 2. Enable ENABLE_FAST_MATH → See FM% change to ~59%
# 3. Enable ENABLE_EXPRESSION_CACHE → See C% change to ~27%
# etc.
"""


# ===== PARSE VALUE OPTIMIZATIONS =====
ENABLE_ULTRA_FAST_PATH = True        # True - Direct integer/color/string detection
ENABLE_FAST_PATH = True              # True - Simple array access and arithmetic  
ENABLE_PARSE_VALUE_CACHE = True      # True - LRU cache for parse_value results
ENABLE_PHASE1_FAST_PATH = True       # True - Simple variable lookups (v_variable only)

# ===== MATH OPTIMIZATIONS =====
ENABLE_FAST_MATH = True              # True - Optimized math expression evaluation
ENABLE_EXPRESSION_CACHE = False       # Cache results of math expressions
ENABLE_JIT = False                    # JIT compilation of expressions

# ===== DEBUGGING AND MONITORING =====
SHOW_OPTIMIZATION_STATUS = True     # Display optimization status at startup

# ===== PREDEFINED PROFILES =====
def set_profile_all_off():
    """Disable all optimizations for baseline testing."""
    global ENABLE_ULTRA_FAST_PATH, ENABLE_FAST_PATH, ENABLE_PARSE_VALUE_CACHE, ENABLE_PHASE1_FAST_PATH, ENABLE_FAST_MATH, ENABLE_EXPRESSION_CACHE, ENABLE_JIT
    
    ENABLE_ULTRA_FAST_PATH = False
    ENABLE_FAST_PATH = False
    ENABLE_PARSE_VALUE_CACHE = False
    ENABLE_PHASE1_FAST_PATH = False
    ENABLE_FAST_MATH = False
    ENABLE_EXPRESSION_CACHE = False
    ENABLE_JIT = False
    print("✓ All optimizations disabled (baseline mode)")

def set_profile_all_on():
    """Enable all optimizations."""
    global ENABLE_ULTRA_FAST_PATH, ENABLE_FAST_PATH, ENABLE_PARSE_VALUE_CACHE, ENABLE_PHASE1_FAST_PATH, ENABLE_FAST_MATH, ENABLE_EXPRESSION_CACHE, ENABLE_JIT
    
    ENABLE_ULTRA_FAST_PATH = True
    ENABLE_FAST_PATH = True
    ENABLE_PARSE_VALUE_CACHE = True
    ENABLE_PHASE1_FAST_PATH = True
    ENABLE_FAST_MATH = True
    ENABLE_EXPRESSION_CACHE = True
    ENABLE_JIT = True
    print("✓ All optimizations enabled")

def set_profile_math_heavy():
    """Optimized for math-heavy scripts like Boids."""
    global ENABLE_ULTRA_FAST_PATH, ENABLE_FAST_PATH, ENABLE_PARSE_VALUE_CACHE, ENABLE_PHASE1_FAST_PATH, ENABLE_FAST_MATH, ENABLE_EXPRESSION_CACHE, ENABLE_JIT
    
    ENABLE_ULTRA_FAST_PATH = False    # Low hit rate on complex expressions
    ENABLE_FAST_PATH = False          # Low hit rate on complex expressions
    ENABLE_PARSE_VALUE_CACHE = False  # Overhead outweighs benefits
    ENABLE_PHASE1_FAST_PATH = True    # High hit rate, good performance
    ENABLE_FAST_MATH = True           # Essential for math-heavy workloads
    ENABLE_EXPRESSION_CACHE = True    # Helps with repeated calculations
    ENABLE_JIT = False                # Compilation overhead too high
    print("✓ Math-heavy profile enabled (optimized for Boids-like scripts)")

def set_profile_simple_graphics():
    """Optimized for simple drawing scripts with basic parameters."""
    global ENABLE_ULTRA_FAST_PATH, ENABLE_FAST_PATH, ENABLE_PARSE_VALUE_CACHE, ENABLE_PHASE1_FAST_PATH, ENABLE_FAST_MATH, ENABLE_EXPRESSION_CACHE, ENABLE_JIT
    
    ENABLE_ULTRA_FAST_PATH = True     # High hit rate on simple values
    ENABLE_FAST_PATH = True           # Good for simple arithmetic
    ENABLE_PARSE_VALUE_CACHE = True   # Benefits from repeated simple lookups
    ENABLE_PHASE1_FAST_PATH = True    # Always beneficial
    ENABLE_FAST_MATH = False          # Minimal math operations
    ENABLE_EXPRESSION_CACHE = False   # Few repeated expressions
    ENABLE_JIT = False                # Overkill for simple scripts
    print("✓ Simple graphics profile enabled")

def set_profile_only_working():
    """Enable only optimizations that showed clear benefits in testing."""
    global ENABLE_ULTRA_FAST_PATH, ENABLE_FAST_PATH, ENABLE_PARSE_VALUE_CACHE, ENABLE_PHASE1_FAST_PATH, ENABLE_FAST_MATH, ENABLE_EXPRESSION_CACHE, ENABLE_JIT
    
    ENABLE_ULTRA_FAST_PATH = False
    ENABLE_FAST_PATH = False
    ENABLE_PARSE_VALUE_CACHE = False
    ENABLE_PHASE1_FAST_PATH = True    # 100% hit rate in testing
    ENABLE_FAST_MATH = True           # 59% hit rate, clear benefit
    ENABLE_EXPRESSION_CACHE = True    # 20-30% hit rate, some benefit
    ENABLE_JIT = False                # High hit rate but poor performance
    print("✓ Only proven optimizations enabled")

def show_status():
    """Display current optimization status."""
    if SHOW_OPTIMIZATION_STATUS:
        print("\n=== Pixil Optimization Status ===")
        print(f"Ultra Fast Path:     {'ON' if ENABLE_ULTRA_FAST_PATH else 'OFF'}")
        print(f"Fast Path:           {'ON' if ENABLE_FAST_PATH else 'OFF'}")
        print(f"Parse Value Cache:   {'ON' if ENABLE_PARSE_VALUE_CACHE else 'OFF'}")
        print(f"Phase 1 Fast Path:   {'ON' if ENABLE_PHASE1_FAST_PATH else 'OFF'}")
        print(f"Fast Math:           {'ON' if ENABLE_FAST_MATH else 'OFF'}")
        print(f"Expression Cache:    {'ON' if ENABLE_EXPRESSION_CACHE else 'OFF'}")
        print(f"JIT Compilation:     {'ON' if ENABLE_JIT else 'OFF'}")
        print("=================================\n")

def set_profile(profile_name):
    """Set optimization profile by name."""
    profile_functions = {
        'all_off': set_profile_all_off,
        'all_on': set_profile_all_on,
        'math_heavy': set_profile_math_heavy,
        'simple_graphics': set_profile_simple_graphics,
        'only_working': set_profile_only_working
    }
    
    if profile_name in profile_functions:
        profile_functions[profile_name]()
        if SHOW_OPTIMIZATION_STATUS:
            show_status()
    else:
        available = ', '.join(profile_functions.keys())
        print(f"Unknown profile '{profile_name}'. Available: {available}")

# Convenience function for quick testing
def quick_test_profile():
    """Quickly set up for testing - disable problematic optimizations."""
    set_profile_only_working()

# Initialize with reasonable defaults on import
if __name__ == "__main__":
    # When run directly, show current status
    print("Pixil Optimization Flags Module")
    show_status()