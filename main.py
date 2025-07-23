import time
import argparse
import json
from src.window_manager import WindowManager
from src.grid_manager import GridManager
from src.element_detector import ElementDetector
from src.solver import Solver, GameBoard
from src.input_manager import InputManager
from src.overlay_manager import OverlayManager

def run_single_cycle(wm, gm, ed, solver, im, om):
    """
    Runs one full cycle of solving and executing.
    
    Returns:
        tuple: A tuple containing (bool: success, float: solve_time_in_seconds).
               solve_time_in_seconds is 0 if no solution was found.
    """
    # --- Step 2: Board State Analysis ---
    om.log("Capturing and analyzing board state...")
    wm.focus()
    time.sleep(0.1) # Give window time to focus
    screenshot = wm.capture()
    
    board = GameBoard(gm)
    identified_elements = ed.identify_elements(screenshot, gm)
    board.update_board_state(identified_elements)
    om.log(f"Board state created with {len(identified_elements)} elements.")

    # --- Step 3: Solving the Puzzle ---
    om.log("Starting solver...")
    start_time = time.time()
    solution_path = solver.solve(board)
    end_time = time.time()
    solve_time = end_time - start_time

    if solution_path:
        om.log(f"Solver finished in {solve_time:.4f} seconds.")
        
        # --- Step 4: Executing the Solution ---
        im.execute_solution(solution_path)
        return True, solve_time # Indicate success and return time
    else:
        om.log("Could not find a solution.")
        return False, solve_time # Indicate failure, but still return the time it took

def main(args):
    """
    Main entry point for the Opus Magnum Automation Bot.
    """
    print("--- Opus Magnum Automation Bot ---")
    try:
        # --- Step 1: Initialization ---
        print("Step 1: Initializing managers...")
        wm = WindowManager()
        gm = GridManager()
        ed = ElementDetector()
        om = OverlayManager(wm.get_window_rect())
        im = InputManager(wm, gm, om)
        solver = Solver(om)

        # Load UI points from config
        with open("config/grid_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        new_game_button_pos = config['ui_points']['start_new_game_button']

        run_count = 0
        # The loop condition is the primary controller. `runs` is -1 for infinite.
        while args.continuous and (args.runs == -1 or run_count < args.runs):
            om.log(f"\n--- Starting Run {run_count + 1} ---")
            
            # Run one cycle, success or failure does not matter for the loop.
            success, solve_time = run_single_cycle(wm, gm, ed, solver, im, om)
            # In the main loop, we don't need to use the solve_time, but we capture it.
            run_count += 1

            # After every cycle, check if we should continue.
            if args.runs == -1 or run_count < args.runs:
                om.log("Cycle complete. Clicking 'Start New Game' and waiting for next puzzle...")
                # Click the "start new game" button
                wm.click(new_game_button_pos['x'], new_game_button_pos['y'])
                time.sleep(5) # Wait for new puzzle to load
            else:
                om.log("All continuous runs completed.")
        
        if not args.continuous:
            success, solve_time = run_single_cycle(wm, gm, ed, solver, im, om)

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure the game is running and configured correctly.")
    finally:
        print("\n--- Automation Finished ---")
        input("Press Enter to exit...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Opus Magnum Automation Bot")
    parser.add_argument(
        '-c', '--continuous',
        nargs='?',
        const=-1,  # Used when '-c' is present without a number, for infinite runs
        default=1,   # Used when '-c' is not present, for a single run
        type=int,
        help="Enable continuous mode. '-c' alone runs infinitely. '-c N' runs N times."
    )
    args = parser.parse_args()

    # Adjust logic based on parsed arguments
    # If -c is not used, args.continuous will be 1.
    # If -c is used alone, it will be -1 (infinite).
    # If -c N is used, it will be N.
    is_continuous_mode = args.continuous != 1
    number_of_runs = args.continuous if args.continuous != 1 else None

    # Create a new args object for clarity in main function
    class RunArgs:
        def __init__(self):
            self.continuous = is_continuous_mode
            self.runs = number_of_runs

    main(RunArgs())