import time
import json
import os
import csv
import numpy as np
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import sys

# --- Path setup ---
# Add the project root to the Python path to allow imports from src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# --- Import core components ---
from src.window_manager import WindowManager
from src.grid_manager import GridManager
from src.element_detector import ElementDetector
from src.solver import Solver
from src.input_manager import InputManager
from src.overlay_manager import OverlayManager
from main import run_single_cycle

# --- Tuner Configuration ---
ANALYSIS_BASE_PATH = "assets/analysis"

def get_baseline_weights():
    """Loads the baseline heuristic weights from the main config file."""
    with open("config/solver_config.json", 'r', encoding='utf-8') as f:
        return json.load(f)['heuristic_weights']

def prepare_output_file(param_name):
    """Creates the directory and CSV file for a parameter, and writes the header if needed."""
    output_dir = os.path.join(ANALYSIS_BASE_PATH, param_name)
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "time.csv")
    
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["parameter_value", "solve_time_s"])
            
    return csv_path

def run_tuning_session(args):
    """Runs a tuning session based on the provided command-line arguments."""
    print("--- Opus Magnum Dynamic Heuristic Tuner ---")
    
    param_to_tune = args.param
    baseline_weights = get_baseline_weights()

    if param_to_tune not in baseline_weights:
        print(f"Error: Parameter '{param_to_tune}' not found in baseline weights.")
        return

    test_values = np.linspace(args.start, args.end, args.steps)
    output_csv_path = prepare_output_file(param_to_tune)
    
    print(f"--- Tuning Parameter: {param_to_tune} ---")
    print(f"Range: {args.start} to {args.end} in {args.steps} steps.")
    print(f"Puzzles per value: {args.puzzles}")
    print(f"Results will be saved to: {output_csv_path}")

    try:
        print("Initializing managers...")
        wm = WindowManager()
        gm = GridManager()
        ed = ElementDetector()
        om = OverlayManager(wm.get_window_rect())
        im = InputManager(wm, gm, om)
        
        with open("config/grid_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        new_game_button_pos = config['ui_points']['start_new_game_button']

        for i, value in enumerate(test_values):
            current_weights = baseline_weights.copy()
            current_weights[param_to_tune] = value
            solver = Solver(overlay_manager=om, heuristic_weights=current_weights)
            
            print(f"  [{i+1}/{len(test_values)}] Testing value: {value:.4f}")
            
            solves_attempted = 0
            puzzles_to_solve = args.puzzles
            
            # Load interrupt config to get the timeout value
            with open("config/interrupt_config.json", 'r', encoding='utf-8') as f:
                interrupt_conf = json.load(f)
            timeout_value = interrupt_conf.get("condition_set", {}).get("conditions", [{}])[0].get("value", 30)


            while solves_attempted < puzzles_to_solve:
                om.log(f"    Run {solves_attempted + 1}/{puzzles_to_solve} for value {value:.4f}")
                success, solve_time = run_single_cycle(wm, gm, ed, solver, im, om)
                
                # Check for success or timeout
                if success:
                    solves_attempted += 1
                    with open(output_csv_path, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([value, solve_time])
                    om.log(f"    Success! Time: {solve_time:.4f}s. Recorded.")
                # If it failed, check if it was due to a timeout
                elif solve_time >= timeout_value * 0.99: # Use 99% threshold to avoid float precision issues
                    solves_attempted += 1
                    with open(output_csv_path, 'a', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow([value, solve_time]) # Record the timeout as a penalty
                    om.log(f"    Timeout after {solve_time:.4f}s. Recorded as penalty and moving on.")
                else:
                    om.log("    Failed to find solution quickly. Retrying with a new puzzle.")

                # Always start a new puzzle to continue the test
                om.log("    Clicking 'Start New Game'...")
                wm.click(new_game_button_pos['x'], new_game_button_pos['y'])
                time.sleep(5)

    except Exception as e:
        print(f"\nAn error occurred during tuning: {e}")
    finally:
        print("\n--- Dynamic Tuning Finished ---")

def plot_results(args):
    """Reads a results CSV and plots a scatter graph with a moving average."""
    print(f"--- Plotting Results for: {args.param} ---")
    
    param_name = args.param
    csv_path = os.path.join(ANALYSIS_BASE_PATH, param_name, "time.csv")
    
    if not os.path.exists(csv_path):
        print(f"Error: Results file not found at '{csv_path}'")
        return

    df = pd.read_csv(csv_path)
    
    # Calculate moving average
    # We sort by parameter_value to ensure the moving average is calculated correctly
    df_sorted = df.sort_values(by='parameter_value')
    df_sorted['moving_avg'] = df_sorted['solve_time_s'].rolling(window=args.window, center=True, min_periods=1).mean()

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 7))

    # Scatter plot for raw data
    ax.scatter(df['parameter_value'], df['solve_time_s'], alpha=0.5, s=15, label='Raw Solve Times')
    
    # Line plot for moving average
    ax.plot(df_sorted['parameter_value'], df_sorted['moving_avg'], color='red', linestyle='--', linewidth=2, label=f'Moving Average (window={args.window})')

    ax.set_title(f'Solver Performance vs. {param_name}', fontsize=16)
    ax.set_xlabel(f'Value of "{param_name}"', fontsize=12)
    ax.set_ylabel('Solve Time (seconds)', fontsize=12)
    ax.legend()
    ax.grid(True)

    output_path = os.path.join(ANALYSIS_BASE_PATH, param_name, f"{param_name}_performance_plot.png")
    plt.savefig(output_path, dpi=300)
    
    print(f"Plot saved successfully to '{output_path}'")

def main():
    parser = argparse.ArgumentParser(description="Opus Magnum Heuristic Tuner and Analyzer.")
    subparsers = parser.add_subparsers(dest='mode', required=True, help='Available modes')

    # --- TUNE mode ---
    parser_tune = subparsers.add_parser('tune', help='Run a tuning session for a specific parameter.')
    parser_tune.add_argument('--param', type=str, required=True, help='The parameter to tune (e.g., "metal_marbles_penalty").')
    parser_tune.add_argument('--start', type=float, required=True, help='The starting value for the tuning range.')
    parser_tune.add_argument('--end', type=float, required=True, help='The ending value for the tuning range.')
    parser_tune.add_argument('--steps', type=int, default=100, help='The number of steps in the tuning range.')
    parser_tune.add_argument('--puzzles', type=int, default=1, help='The number of puzzles to solve for each value.')
    parser_tune.set_defaults(func=run_tuning_session)

    # --- PLOT mode ---
    parser_plot = subparsers.add_parser('plot', help='Plot the results from a tuning session.')
    parser_plot.add_argument('--param', type=str, required=True, help='The parameter whose results you want to plot.')
    parser_plot.add_argument('--window', type=int, default=10, help='The window size for the moving average calculation.')
    parser_plot.set_defaults(func=plot_results)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()