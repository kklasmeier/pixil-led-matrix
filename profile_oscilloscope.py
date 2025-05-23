# simple_profiler.py - Avoids the queue cleanup bug
import cProfile
import pstats
import time
import io

def create_mock_execute_command():
    """Create a mock execute function that doesn't use the real queue."""
    command_count = 0
    
    def mock_execute(command):
        nonlocal command_count
        command_count += 1
        # Just count commands, don't actually execute
        if command_count % 100 == 0:  # Progress indicator
            print(f".", end="", flush=True)
        return command
    
    return mock_execute, lambda: command_count

def profile_pixil_parsing():
    """Profile just the parsing/processing part, not the RGB matrix execution."""
    
    # Create test script focused on your performance concerns
    test_script = """
clear()
v_table_size = 32
create_array(v_sine_table, 32)
create_array(v_channel_colors, 3, string)
v_channel_colors[0] = "lime"
v_channel_colors[1] = "cyan"  
v_channel_colors[2] = "yellow"

# Pre-calculate sine table (like your script)
for v_i in (0, 31, 1)
    v_angle = v_i * 6.28318530718 / 32
    v_sine_table[v_i] = sin(v_angle) * 100
endfor v_i

# Simulate your oscilloscope pattern
for v_frame in (0, 19, 1)
    begin_frame
    
    # Grid drawing (simpler)
    for v_x in (0, 63, 16)
        plot(v_x, 32, gray, 40)
    endfor v_x
    
    # Three channels like your script
    for v_ch in (0, 2, 1)
        for v_x in (0, 63, 4)
            # Complex expression like yours
            v_table_index = (v_frame * 2 + v_x * 2 + v_ch * 16) % v_table_size
            v_wave_value = v_sine_table[v_table_index]
            v_y = 16 + v_ch * 16 + (v_wave_value / 5)
            
            # Bounds checking like yours
            if v_y < 1 then
                v_y = 1
            endif
            if v_y > 62 then
                v_y = 62
            endif
            
            # Drawing with array-based color
            plot(v_x, v_y, v_channel_colors[v_ch], 90)
        endfor v_x
    endfor v_ch
    
    end_frame
endfor v_frame
"""

    script_file = 'test_profile.pix'
    
    try:
        # Write test script
        with open(script_file, 'w') as f:
            f.write(test_script)
        
        print("Starting performance analysis...")
        print("Processing", end="", flush=True)
        
        # Create mock execute function to avoid queue issues
        mock_execute, get_count = create_mock_execute_command()
        
        # Start profiling
        pr = cProfile.Profile()
        pr.enable()
        
        start_time = time.time()
        
        # Import Pixil and run just the parsing/processing
        import Pixil
        
        # Temporarily override the variables and other globals to avoid the cleanup bug
        old_variables = getattr(Pixil, 'variables', {})
        old_frame_commands = getattr(Pixil, 'frame_commands', [])
        old_in_frame_mode = getattr(Pixil, 'in_frame_mode', False)
        
        try:
            # Process the script with our mock execute function
            Pixil.process_script(script_file, mock_execute)
            
        except Exception as e:
            if "queue_instance" in str(e):
                print(f"\n\nCaught expected queue error: {e}")
                print("This is expected - we're only profiling the parsing, not execution")
            else:
                print(f"\n\nUnexpected error: {e}")
        
        end_time = time.time()
        pr.disable()
        
        execution_time = end_time - start_time
        command_count = get_count()
        
        print(f"\n\nParsing completed!")
        print(f"Execution time: {execution_time:.3f} seconds")
        print(f"Commands generated: {command_count}")
        print(f"Commands per second: {command_count/execution_time:.1f}")
        
        # Analyze results
        print("\n" + "="*60)
        print("PERFORMANCE ANALYSIS RESULTS")
        print("="*60)
        
        # Create string buffer for stats
        s = io.StringIO()
        stats = pstats.Stats(pr, stream=s)
        
        # Print top functions by cumulative time
        print("\nTOP 15 FUNCTIONS BY CUMULATIVE TIME:")
        print("-" * 60)
        stats.sort_stats('cumulative')
        stats.print_stats(15)
        
        # Print top functions by self time
        print("\nTOP 15 FUNCTIONS BY SELF TIME:")
        print("-" * 60)
        stats.sort_stats('tottime')  
        stats.print_stats(15)
        
        # Look for Pixil-specific functions
        print("\nPIXIL PARSING FUNCTIONS:")
        print("-" * 60)
        
        pixil_stats = []
        for func_info, timing in stats.stats.items():
            func_name = func_info[2]
            if any(keyword in func_name for keyword in 
                   ['parse_value', 'evaluate', 'process_lines', 'substitute', 'format_parameter']):
                calls, total_calls, tottime, cumtime = timing[:4]
                pixil_stats.append((func_name, calls, tottime, cumtime))
        
        # Sort by cumulative time
        pixil_stats.sort(key=lambda x: x[3], reverse=True)
        
        print(f"{'Function':<35} {'Calls':<8} {'Self(s)':<8} {'Cumul(s)':<8}")
        print("-" * 65)
        for func_name, calls, tottime, cumtime in pixil_stats[:10]:
            # Shorten long function names
            if len(func_name) > 32:
                func_name = "..." + func_name[-29:]
            print(f"{func_name:<35} {calls:<8} {tottime:<8.4f} {cumtime:<8.4f}")
        
        # Save full report
        with open('pixil_profile.txt', 'w') as f:
            stats = pstats.Stats(pr, stream=f)
            stats.sort_stats('cumulative')
            stats.print_stats()
        
        print(f"\nFull report saved to: pixil_profile.txt")
        
        # Performance summary
        print(f"\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Total script processing time: {execution_time:.3f} seconds")
        print(f"Commands generated: {command_count}")
        print(f"Average time per command: {(execution_time/command_count)*1000:.2f} ms")
        
        # Estimate full script performance
        estimated_full_time = execution_time * 10  # Your full script is ~10x larger
        print(f"Estimated time for full oscilloscope script: {estimated_full_time:.1f} seconds")
        
        return True
        
    except Exception as e:
        print(f"\nError during profiling: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Cleanup
        try:
            import os
            os.remove(script_file)
        except:
            pass

if __name__ == "__main__":
    print("SIMPLE PIXIL PROFILER")
    print("====================")
    print("This profiles only the parsing/processing, not RGB matrix execution")
    print()
    
    success = profile_pixil_parsing()
    
    if success:
        print("\n" + "="*60)
        print("Check the file 'pixil_profile.txt' for detailed results!")
        print("="*60)
    
    print("\nProfiling complete!")