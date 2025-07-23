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

# --- Analyzer Configuration ---
ANALYSIS_OUTPUT_PATH = "assets/analysis/total"

def prepare_output_file():
    """Creates the directory and CSV file for the analysis, and writes the header if needed."""
    os.makedirs(ANALYSIS_OUTPUT_PATH, exist_ok=True)
    csv_path = os.path.join(ANALYSIS_OUTPUT_PATH, "performance.csv")
    
    if not os.path.exists(csv_path):
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["solver_time_s", "other_time_s"])
            
    return csv_path

def run_analysis_session(args):
    """Runs a performance analysis session."""
    print("--- Opus Magnum Performance Analyzer ---")
    
    output_csv_path = prepare_output_file()
    
    print(f"Number of runs: {args.runs}")
    print(f"Results will be saved to: {output_csv_path}")

    try:
        print("Initializing managers...")
        wm = WindowManager()
        gm = GridManager()
        ed = ElementDetector()
        om = OverlayManager(wm.get_window_rect())
        im = InputManager(wm, gm, om)
        solver = Solver(overlay_manager=om) # Use default weights
        
        with open("config/grid_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        new_game_button_pos = config['ui_points']['start_new_game_button']

        for i in range(args.runs):
            om.log(f"--- Starting Run {i + 1}/{args.runs} ---")
            
            total_start_time = time.time()
            success, solver_time = run_single_cycle(wm, gm, ed, solver, im, om)
            total_time = time.time() - total_start_time
            
            other_time = total_time - solver_time
            
            if success:
                om.log(f"    Success! Total: {total_time:.4f}s, Solver: {solver_time:.4f}s, Other: {other_time:.4f}s.")
                with open(output_csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([solver_time, other_time])
            else:
                om.log(f"    Failed. Total: {total_time:.4f}s, Solver: {solver_time:.4f}s. Not recording.")

            # Always start a new puzzle to continue the test
            if i < args.runs - 1:
                om.log("    Clicking 'Start New Game'...")
                wm.click(new_game_button_pos['x'], new_game_button_pos['y'])
                time.sleep(5)

    except Exception as e:
        print(f"\nAn error occurred during analysis: {e}")
    finally:
        print("\n--- Performance Analysis Finished ---")

def plot_results(args):
    """Reads the results CSV and plots histograms of the recorded times."""
    print("--- Plotting Performance Results ---")
    
    csv_path = os.path.join(ANALYSIS_OUTPUT_PATH, "performance.csv")
    
    if not os.path.exists(csv_path):
        print(f"Error: Results file not found at '{csv_path}'")
        return

    df = pd.read_csv(csv_path)
    
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Solver Time Histogram
    ax1.hist(df['solver_time_s'], bins=args.bins, color='skyblue', edgecolor='black')
    ax1.set_title('Solver Time Distribution', fontsize=16)
    ax1.set_xlabel('Time (seconds)', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.axvline(df['solver_time_s'].mean(), color='r', linestyle='dashed', linewidth=1, label=f"Mean: {df['solver_time_s'].mean():.2f}s")
    ax1.legend()

    # Other Time Histogram
    ax2.hist(df['other_time_s'], bins=args.bins, color='lightgreen', edgecolor='black')
    ax2.set_title('Other Time Distribution (Capture, Input, etc.)', fontsize=16)
    ax2.set_xlabel('Time (seconds)', fontsize=12)
    ax2.set_ylabel('Frequency') # No need to repeat
    ax2.axvline(df['other_time_s'].mean(), color='r', linestyle='dashed', linewidth=1, label=f"Mean: {df['other_time_s'].mean():.2f}s")
    ax2.legend()

    fig.suptitle('Performance Analysis Histograms', fontsize=20)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    output_path = os.path.join(ANALYSIS_OUTPUT_PATH, "performance_histogram.png")
    plt.savefig(output_path, dpi=300)
    
    print(f"Plot saved successfully to '{output_path}'")

def plot_throughput(cutoff_values, throughput_values, best_cutoff, best_throughput):
    """Plots the throughput vs. cutoff time graph."""
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 7))

    ax.plot(cutoff_values, throughput_values, label='Throughput vs. Cutoff Time')
    
    # Highlight the optimal point
    ax.axvline(x=best_cutoff, color='r', linestyle='--', label=f'Optimal Cutoff: {best_cutoff:.2f}s')
    ax.scatter([best_cutoff], [best_throughput], color='red', zorder=5)
    ax.annotate(f'Max Throughput: {best_throughput:.4f} solves/sec',
                xy=(best_cutoff, best_throughput),
                xytext=(best_cutoff + 0.5, best_throughput),
                arrowprops=dict(facecolor='black', shrink=0.05))

    ax.set_title('Optimal Timeout Estimation', fontsize=16)
    ax.set_xlabel('Cutoff Time (seconds)', fontsize=12)
    ax.set_ylabel('Throughput (Solves per Second)', fontsize=12)
    ax.legend()
    ax.grid(True)

    output_path = os.path.join(ANALYSIS_OUTPUT_PATH, "optimal_timeout_plot.png")
    plt.savefig(output_path, dpi=300)
    print(f"\nThroughput plot saved to '{output_path}'")


def estimate_optimal_timeout(args):
    """Reads performance data and estimates the optimal solver timeout."""
    print("--- Optimal Timeout Estimator ---")
    
    csv_path = os.path.join(ANALYSIS_OUTPUT_PATH, "performance.csv")
    if not os.path.exists(csv_path):
        print(f"Error: Performance data file not found at '{csv_path}'.")
        print("Please run the 'run' mode first to collect data.")
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print("Performance data is empty. Cannot estimate.")
        return

    # --- Theoretical Analysis ---
    print("\n--- Theoretical Model (Final) ---")
    print("Goal: Maximize throughput (solves per unit of time).")
    print("Let t_cutoff be the solver timeout, and T_load be the fixed time to load a new puzzle (10s).")
    print("For each attempt:")
    print("  - If solve_time <= t_cutoff: Success!")
    print("    Cost = solve_time + other_time (action + load). Solves = 1.")
    print("  - If solve_time > t_cutoff: Failure (Timeout).")
    print("    Cost = t_cutoff + T_load. Solves = 0.")
    print("Throughput(t_cutoff) = Total Solves / Total Cost\n")

    # --- Calculation ---
    print("--- Calculating Optimal Timeout ---")
    T_load = 10.0  # Fixed 10-second penalty for loading new puzzle, as per user request.
    solver_times = df['solver_time_s'].values
    other_times = df['other_time_s'].values
    
    # Test a range of cutoff values from 0 to the max observed solver time
    max_time = solver_times.max()
    cutoff_values = np.linspace(0, max_time, num=args.steps)
    
    throughputs = []
    
    for t_cutoff in cutoff_values:
        success_mask = solver_times <= t_cutoff
        
        n_success = np.sum(success_mask)
        n_fail = len(solver_times) - n_success
        
        # Final, most accurate formula
        cost_success = np.sum(solver_times[success_mask]) + np.sum(other_times[success_mask])
        cost_fail = n_fail * (t_cutoff + T_load)
        total_cost = cost_success + cost_fail
        
        if total_cost == 0:
            throughput = 0
        else:
            throughput = n_success / total_cost
        
        throughputs.append(throughput)

    # Find the best result
    throughputs = np.array(throughputs)
    best_idx = np.argmax(throughputs)
    best_cutoff = cutoff_values[best_idx]
    best_throughput = throughputs[best_idx]

    print("\n--- Results ---")
    print(f"Based on {len(df)} data points:")
    print(f"Optimal Solver Cutoff Time: {best_cutoff:.4f} seconds.")
    print(f"  - Expected Throughput: {best_throughput:.4f} solves/sec")
    print(f"  - Expected Solves per Minute: {best_throughput * 60:.2f}")
    print(f"  - Expected Solves per Hour: {best_throughput * 3600:.2f}")

    if args.plot:
        plot_throughput(cutoff_values, throughputs, best_cutoff, best_throughput)


def main():
    parser = argparse.ArgumentParser(description="Opus Magnum Performance Analyzer.")
    subparsers = parser.add_subparsers(dest='mode', required=True, help='Available modes')

    # --- RUN mode ---
    parser_run = subparsers.add_parser('run', help='Run a performance analysis session.')
    parser_run.add_argument('--runs', type=int, default=10, help='The number of puzzles to solve.')
    parser_run.set_defaults(func=run_analysis_session)

    # --- PLOT mode ---
    parser_plot = subparsers.add_parser('plot', help='Plot the results from an analysis session.')
    parser_plot.add_argument('--bins', type=int, default=20, help='The number of bins for the histogram.')
    parser_plot.set_defaults(func=plot_results)

    # --- ESTIMATE mode ---
    parser_estimate = subparsers.add_parser('estimate', help='Estimate the optimal solver timeout from existing data.')
    parser_estimate.add_argument('--steps', type=int, default=500, help='Number of cutoff values to test.')
    parser_estimate.add_argument('--plot', action='store_true', help='Generate a plot of the throughput analysis.')
    parser_estimate.set_defaults(func=estimate_optimal_timeout)


    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()