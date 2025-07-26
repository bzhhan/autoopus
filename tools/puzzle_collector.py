import os
import time
import random
import json
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.grid_manager import GridManager
from src.solver import Solver, GameBoard
from src.overlay_manager import OverlayManager
from src.window_manager import WindowManager
from src.element_detector import ElementDetector
from src.input_manager import InputManager
from tools.puzzle_recorder import PuzzleRecorder

def run_single_cycle(wm, gm, ed, solver, im, om, collector):
    """
    Runs one full cycle of capturing, solving and recording.
    
    Returns:
        tuple: A tuple containing (bool: success, float: solve_time_in_seconds).
    """
    # --- Step 1: Board State Analysis ---
    om.log("Capturing and analyzing board state...")
    wm.focus()
    time.sleep(0.1) # Give window time to focus
    screenshot = wm.capture()
    
    board = GameBoard(gm)
    identified_elements = ed.identify_elements(screenshot, gm)
    board.update_board_state(identified_elements)
    om.log(f"Board state created with {len(identified_elements)} elements.")

    # --- Step 2: Solving the Puzzle ---
    om.log("Starting solver...")
    start_time = time.time()
    solution_path = solver.solve(board)
    end_time = time.time()
    solve_time = end_time - start_time

    if solution_path:
        om.log(f"Solver finished in {solve_time:.4f} seconds.")
        
        # --- Step 3: Record the puzzle ---
        category_name, category_details = collector.get_category(solve_time)
        if category_name and category_details["count"] < collector.max_per_category:
            collector.save_puzzle(board, solution_path, solve_time, category_name, category_details)
            category_details["count"] += 1
            om.log(f"Saved puzzle in category {category_name}. Total: {category_details['count']}/{collector.max_per_category}")
            collector.print_status_to_overlay(om)
        else:
            if category_name:
                om.log(f"Category {category_name} is full. Discarding puzzle.")
        
        # --- Step 4: Execute the Solution (optional, for demonstration) ---
        # im.execute_solution(solution_path)
        return True, solve_time
    else:
        om.log(f"Could not find a solution after {solve_time:.4f} seconds.")
        
        # --- Step 3: Record the unsolvable puzzle ---
        # noanswer category has no limit, always save
        collector.save_unsolvable_puzzle(board, solve_time)
        collector.noanswer_category["count"] += 1
        
        # Only count as valid if solve_time > 0
        if solve_time > 0:
            collector.noanswer_category["valid_count"] += 1
            om.log(f"Saved unsolvable puzzle. Total: {collector.noanswer_category['count']} (valid: {collector.noanswer_category['valid_count']})")
        else:
            om.log(f"Saved 0-second unsolvable puzzle (not counted as valid). Total: {collector.noanswer_category['count']} (valid: {collector.noanswer_category['valid_count']})")
        
        collector.print_status_to_overlay(om)
        
        return False, solve_time

class PuzzleCollector:
    def __init__(self, base_dir="collected_puzzles"):
        self.base_dir = base_dir
        self.recorder = PuzzleRecorder(recording_dir=base_dir)
        self.time_categories = {
            "0-1s": {"min": 0, "max": 1, "path": os.path.join(base_dir, "0-1s"), "count": 0},
            "1-10s": {"min": 1, "max": 10, "path": os.path.join(base_dir, "1-10s"), "count": 0},
            "10-60s": {"min": 10, "max": 60, "path": os.path.join(base_dir, "10-60s"), "count": 0},
            "60-300s": {"min": 60, "max": 300, "path": os.path.join(base_dir, "60-300s"), "count": 0},
            "300-1500s": {"min": 300, "max": 1500, "path": os.path.join(base_dir, "300-1500s"), "count": 0},
            "1500-3600s": {"min": 1500, "max": 3600, "path": os.path.join(base_dir, "1500-3600s"), "count": 0},
            "3600s+": {"min": 3600, "max": float('inf'), "path": os.path.join(base_dir, "3600s+"), "count": 0},
        }
        # Add noanswer category for unsolvable puzzles
        self.noanswer_category = {
            "path": os.path.join(base_dir, "noanswer"),
            "count": 0,  # Total saved files
            "valid_count": 0  # Valid count (excluding 0-second solves)
        }
        self.max_per_category = 10
        self._setup_directories()

    def _setup_directories(self):
        for category in self.time_categories.values():
            os.makedirs(category["path"], exist_ok=True)
            category["count"] = len([name for name in os.listdir(category["path"]) if name.endswith('.json')])
        
        # Setup noanswer directory
        os.makedirs(self.noanswer_category["path"], exist_ok=True)
        noanswer_files = [name for name in os.listdir(self.noanswer_category["path"]) if name.endswith('.json')]
        self.noanswer_category["count"] = len(noanswer_files)
        
        # Count valid noanswer files (excluding 0-second solves)
        valid_count = 0
        for filename in noanswer_files:
            if not filename.startswith("puzzle_noanswer_0s_"):
                valid_count += 1
        self.noanswer_category["valid_count"] = valid_count

    def get_category(self, solve_time):
        for name, details in self.time_categories.items():
            if details["min"] <= solve_time < details["max"]:
                return name, details
        return None, None

    def run_collection(self):
        print("--- Opus Magnum Puzzle Collector ---")
        try:
            # --- Step 1: Initialization (similar to main.py) ---
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

            om.log("Starting puzzle collection...")
            self.print_status_to_overlay(om)

            run_count = 0
            # Continue until all categories are full
            while not self.all_categories_full():
                run_count += 1
                om.log(f"\n--- Starting Run {run_count} ---")
                
                # Run one cycle
                success, solve_time = run_single_cycle(wm, gm, ed, solver, im, om, self)
                
                # Check if we should continue
                if not self.all_categories_full():
                    om.log("Cycle complete. Clicking 'Start New Game' and waiting for next puzzle...")
                    # Click the "start new game" button
                    wm.click(new_game_button_pos['x'], new_game_button_pos['y'])
                    time.sleep(5) # Wait for new puzzle to load
                else:
                    om.log("All categories completed.")

            om.log("All categories are full. Collection complete.")
            
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            print("Please ensure the game is running and configured correctly.")
        finally:
            print("\n--- Collection Finished ---")
            input("Press Enter to exit...")

    def save_puzzle(self, board, solution_path, solve_time, category_name, category_details):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"puzzle_{int(round(solve_time))}s_{timestamp}.json"
        filepath = os.path.join(category_details["path"], filename)
        self.recorder.record(board.hex_states, solution_path, puzzle_name=filepath)

    def save_unsolvable_puzzle(self, board, solve_time):
        """Save an unsolvable puzzle to the noanswer category."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"puzzle_noanswer_{int(round(solve_time))}s_{timestamp}.json"
        filepath = os.path.join(self.noanswer_category["path"], filename)
        # For unsolvable puzzles, we pass an empty solution path
        self.recorder.record(board.hex_states, [], puzzle_name=filepath)

    def all_categories_full(self):
        time_categories_full = all(cat["count"] >= self.max_per_category for cat in self.time_categories.values())
        # Stop if all time categories are full AND noanswer has more than 50 valid puzzles
        noanswer_over_limit = self.noanswer_category["valid_count"] > 50
        return time_categories_full and noanswer_over_limit

    def print_status_to_overlay(self, om):
        """Print collection status to overlay manager."""
        om.log("--- Collection Status ---")
        for name, details in self.time_categories.items():
            progress_bar = '█' * details['count'] + '░' * (self.max_per_category - details['count'])
            om.log(f"{name:<12} [{progress_bar}] {details['count']}/{self.max_per_category}")
        
        # Show noanswer category status (unlimited, but show warning if valid_count >50)
        total_count = self.noanswer_category['count']
        valid_count = self.noanswer_category['valid_count']
        if valid_count <= 50:
            noanswer_display = f"{'noanswer':<12} [{'█' * min(valid_count, 10)}{'░' * max(0, 10-valid_count)}] {total_count}/∞ (valid: {valid_count})"
        else:
            noanswer_display = f"{'noanswer':<12} [{'█' * 10}] {total_count}/∞ (valid: {valid_count}, >50 will stop when others full)"
        om.log(noanswer_display)


if __name__ == "__main__":
    collector = PuzzleCollector()
    collector.run_collection()