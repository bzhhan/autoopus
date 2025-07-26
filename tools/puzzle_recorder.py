import os
import json
import copy
from datetime import datetime
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import math
import argparse
import time
from PIL import Image, ImageTk

import threading
import queue
# Add the project root to the Python path to allow imports from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.grid_manager import GridManager
from src.window_manager import WindowManager
from src.element_detector import ElementDetector
from src.solver import Solver, GameBoard


class PuzzleRecorder:
    """
    Handles the recording of puzzle states and their solutions.
    """
    def __init__(self, recording_dir="recordings"):
        self.recording_dir = recording_dir
        if not os.path.exists(self.recording_dir):
            os.makedirs(self.recording_dir)

    def record(self, board_state, solution_path, puzzle_name=None):
        if puzzle_name:
            # If a full path is provided, use it directly
            if os.path.dirname(puzzle_name):
                 filepath = puzzle_name
            else:
                 filename = f"{puzzle_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                 filepath = os.path.join(self.recording_dir, filename)
        else:
            filename = f"puzzle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.recording_dir, filename)


        recording_data = {
            "puzzle_name": puzzle_name if puzzle_name else "Unnamed Puzzle",
            "timestamp": datetime.now().isoformat(),
            "initial_board_state": board_state,
            "solution_path": solution_path
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(recording_data, f, indent=4)
            print(f"Successfully recorded puzzle to {filepath}")
            return filepath
        except IOError as e:
            print(f"Error: Could not write to file {filepath}. Reason: {e}")
            return None

class PuzzleSimulator:
    """
    An interactive simulator for playing a puzzle.
    It encapsulates the game logic from the original GameBoard.
    """
    def __init__(self, grid_manager):
        self.grid = grid_manager
        self.hex_states = [{"element": "UNKNOWN", "state": "normal"}] * len(self.grid.hex_centers)
        self.metal_transmutation_order = ["LEAD", "TIN", "IRON", "COPPER", "SILVER", "GOLD"]
        self.move_history = []

    def load_board_state(self, board_state):
        """Loads a board state and resets the history."""
        if len(board_state) != len(self.hex_states):
            raise ValueError("Mismatch between loaded board state and grid size.")
        self.hex_states = copy.deepcopy(board_state)
        self.move_history = []
        self._update_unlock_status()

    def _update_unlock_status(self):
        for i, hex_info in enumerate(self.hex_states):
            if hex_info["element"] in ["EMPTY", "OUT_OF_BOUNDS", "UNKNOWN"]:
                self.hex_states[i]['unlocked'] = True
                continue
            
            # Check basic geometric unlock condition (3 consecutive empty neighbors)
            neighbor_indices = self.grid.neighbors[i]
            neighbor_is_empty = []
            for neighbor_idx in neighbor_indices:
                if neighbor_idx == -1 or self.hex_states[neighbor_idx]["element"] == "EMPTY":
                    neighbor_is_empty.append(True)
                else:
                    neighbor_is_empty.append(False)
            
            is_empty_circular = neighbor_is_empty + neighbor_is_empty[:2]
            geometric_unlocked = False
            for j in range(len(neighbor_is_empty)):
                if all(is_empty_circular[j:j+3]):
                    geometric_unlocked = True
                    break
            
            # For metals, also check if prerequisite metals are unlocked
            element = hex_info["element"]
            if element in self.metal_transmutation_order and geometric_unlocked:
                metal_unlocked = self._is_metal_unlocked(element)
                self.hex_states[i]['unlocked'] = metal_unlocked
            else:
                self.hex_states[i]['unlocked'] = geometric_unlocked
    
    def _is_metal_unlocked(self, metal_element):
        """Check if a metal element should be unlocked based on metal transmutation rules."""
        if metal_element not in self.metal_transmutation_order:
            return True
        
        metal_index = self.metal_transmutation_order.index(metal_element)
        
        # LEAD (index 0) is always unlocked if geometrically unlocked
        if metal_index == 0:
            return True
        
        # For other metals, check if ALL lower-rank metals are completely removed from the board
        for i in range(metal_index):
            lower_metal = self.metal_transmutation_order[i]
            # If any lower-rank metal still exists on the board, this metal cannot be unlocked
            for hex_state in self.hex_states:
                if hex_state["element"] == lower_metal:
                    return False
        
        # All lower-rank metals have been removed, so this metal can be unlocked
        return True

    def _is_valid_match(self, idx1, idx2):
        e1 = self.hex_states[idx1]["element"]
        e2 = self.hex_states[idx2]["element"]
        basic_elements = ["FIRE", "WATER", "EARTH", "AIR"]
        metals = self.metal_transmutation_order
        if e1 in basic_elements and e1 == e2: return True
        if e1 == "SALT" and (e2 in basic_elements or e2 == "SALT"): return True
        if e2 == "SALT" and (e1 in basic_elements or e1 == "SALT"): return True
        if (e1 == "VITAE" and e2 == "MORS") or (e1 == "MORS" and e2 == "VITAE"): return True
        if e1 == "QUICKSILVER" and e2 in metals and e2 != "QUICKSILVER":
            return self._is_lowest_rank_metal(e2)
        if e2 == "QUICKSILVER" and e1 in metals and e1 != "QUICKSILVER":
            return self._is_lowest_rank_metal(e1)
        return False

    def _is_lowest_rank_metal(self, metal_element):
        current_metals_on_board = {h["element"] for h in self.hex_states if h["element"] in self.metal_transmutation_order}
        lowest_metal_on_board = next((metal for metal in self.metal_transmutation_order if metal in current_metals_on_board), None)
        return metal_element == lowest_metal_on_board

    def attempt_move(self, idx1, idx2):
        """Attempts to perform a move, returns True if successful."""
        if not (self.hex_states[idx1].get('unlocked', False) and self.hex_states[idx2].get('unlocked', False)):
            return False # Both must be unlocked
        
        if not self._is_valid_match(idx1, idx2):
            return False # Must be a valid pair

        move = tuple(sorted((idx1, idx2)))
        self.move_history.append(copy.deepcopy(self.hex_states))
        self.hex_states[idx1] = {"element": "EMPTY", "state": "normal"}
        self.hex_states[idx2] = {"element": "EMPTY", "state": "normal"}
        self._update_unlock_status()
        return True

    def eliminate_single_element(self, idx):
        """Eliminates a single element, used for GOLD."""
        if not self.hex_states[idx].get('unlocked', False):
            return False
        
        self.move_history.append(copy.deepcopy(self.hex_states))
        self.hex_states[idx] = {"element": "EMPTY", "state": "normal"}
        self._update_unlock_status()
        return True

    def undo_move(self):
        """Reverts the board to the state before the last move."""
        if not self.move_history:
            return False
        self.hex_states = self.move_history.pop()
        return True

    def is_solved(self):
        """Checks if the puzzle is solved (no elements left on the board)."""
        remaining_elements = [h['element'] for h in self.hex_states if h['element'] not in ["EMPTY", "OUT_OF_BOUNDS", "UNKNOWN"]]
        return not remaining_elements

    def get_unlocked_indices(self):
        return [i for i, h in enumerate(self.hex_states) if h.get('unlocked', False)]

    def get_current_game_board(self):
        """Creates and returns a GameBoard object from the current simulator state."""
        board = GameBoard(self.grid)
        board.update_board_state(self.hex_states)
        return board

# A simple logger class that redirects solver progress to the GUI label
class GUILogger:
    def __init__(self, label):
        self.label = label

    def log(self, message):
        # Truncate long messages for display
        display_message = (message[:70] + '...') if len(message) > 70 else message
        self.label.config(text=display_message)
        self.label.master.update_idletasks()
        print(message) # Also print full message to console

    def update_last_line(self, message):
        # For a simple label, updating is the same as logging.
        self.log(message)

class PuzzleReplayGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Opus Magnum - Puzzle Simulator")
        
        # Core components
        self.grid_manager = GridManager()
        self.simulator = PuzzleSimulator(self.grid_manager)
        # Defer solver creation until logger is ready
        
        # State variables
        self.selected_hex_index = None
        self.solution_path = None
        self.hinted_move = None
        self.draw_offsets = {'x': 0, 'y': 0, 'padding': 20}

        # For solver threading
        self.result_queue = queue.Queue()
        self.solving_thread = None

        # Load game assets
        self.background_image = None
        self.element_images = {}
        self._load_assets()

        # --- UI Layout ---
        main_frame = tk.Frame(master)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas on the left
        canvas_frame = tk.Frame(main_frame)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas = tk.Canvas(canvas_frame, bg='gray20')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # Controls on the right
        controls_frame = tk.Frame(main_frame, width=400)
        controls_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
        controls_frame.pack_propagate(False) # Prevent the frame from resizing to fit its contents

        self.info_label = tk.Label(controls_frame, text="Load a puzzle to begin.", font=("Arial", 12), wraplength=300, height=2, justify='left', anchor='nw')
        self.info_label.pack(pady=10, fill=tk.X)

        # Create logger and solver
        self.gui_logger = GUILogger(self.info_label)
        self.solver = Solver(self.gui_logger)

        self.load_button = tk.Button(controls_frame, text="Load Puzzle", command=self.prompt_load_puzzle)
        self.load_button.pack(pady=5, fill=tk.X)
        
        self.undo_button = tk.Button(controls_frame, text="Undo Move", command=self.undo_move, state=tk.DISABLED)
        self.undo_button.pack(pady=5, fill=tk.X)

        # Solver controls
        tk.Label(controls_frame, text="--- Solver ---").pack(pady=(20, 5))
        self.solve_button = tk.Button(controls_frame, text="Solve Puzzle", command=self.solve_puzzle, state=tk.DISABLED)
        self.solve_button.pack(pady=5, fill=tk.X)
        
        self.hint_button = tk.Button(controls_frame, text="Next Move Hint", command=self.show_next_move_hint, state=tk.DISABLED)
        self.hint_button.pack(pady=5, fill=tk.X)

        # Fallback colors
        self.element_colors = {
            "EMPTY": "gray30", "UNKNOWN": "purple", "OUT_OF_BOUNDS": "black", "SALT": "white",
            "WATER": "blue", "FIRE": "red", "EARTH": "brown", "AIR": "light blue", "VITAE": "pink",
            "MORS": "dark green", "LEAD": "gray50", "TIN": "gray70", "IRON": "dark orange",
            "COPPER": "orange", "SILVER": "silver", "GOLD": "gold", "QUICKSILVER": "cyan"
        }
        
        self.draw_board()

    def _load_assets(self):
        """Load background image and element templates."""
        try:
            # Load background image
            bg_path = os.path.join("assets", "gui", "background.png")
            if os.path.exists(bg_path):
                self.background_image = Image.open(bg_path)
                print(f"Loaded background image: {bg_path}")
            else:
                print(f"Warning: Background image not found at {bg_path}")
            
            # Load element templates
            templates_dir = os.path.join("assets", "gui", "templates")
            if os.path.exists(templates_dir):
                hex_size = self.grid_manager.hex_size
                # Apply the 0.7 scaling factor from grid_config.json
                target_size = int(hex_size * 2 * 0.7)  # Scale images according to sampling_radius_ratio
                
                for filename in os.listdir(templates_dir):
                    if filename.endswith('.png'):
                        # Parse filename: ELEMENT_STATE_##.png
                        name_parts = filename.replace('.png', '').split('_')
                        if len(name_parts) >= 2:
                            element = name_parts[0]
                            state = name_parts[1]  # 'normal' or 'darkened'
                            
                            # Load and resize image
                            img_path = os.path.join(templates_dir, filename)
                            img = Image.open(img_path)
                            img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
                            
                            # Convert to PhotoImage for tkinter
                            photo = ImageTk.PhotoImage(img)
                            
                            # Store with key format: ELEMENT_STATE
                            key = f"{element}_{state}"
                            self.element_images[key] = photo
                
                print(f"Loaded {len(self.element_images)} element images")
            else:
                print(f"Warning: Templates directory not found at {templates_dir}")
                
        except Exception as e:
            print(f"Error loading assets: {e}")

    def draw_hexagon(self, x, y, size, color, outline_color="white", outline_width=1):
        points = [(x + size * math.cos(math.pi / 180 * (60 * i - 30)), y + size * math.sin(math.pi / 180 * (60 * i - 30))) for i in range(6)]
        self.canvas.create_polygon(points, fill=color, outline=outline_color, width=outline_width)

    def darken_color(self, color_name):
        """Darkens a given color name by picking a darker version."""
        # This is a simple approach. For more complex color manipulation, a library would be better.
        dark_map = {
            "blue": "#00008B", "red": "#8B0000", "brown": "#5C4033", "light blue": "#5F9EA0",
            "pink": "#C71585", "dark green": "#006400", "gray50": "#363636", "gray70": "#4F4F4F",
            "dark orange": "#BF4F00", "orange": "#CD853F", "silver": "#808080", "gold": "#B8860B",
            "cyan": "#008B8B", "white": "gray25"
        }
        return dark_map.get(color_name, "gray15")

    def draw_board(self):
        """Draws the entire board state on the canvas using game assets."""
        self.canvas.delete("all")
        if not self.simulator.hex_states or not any(h.get('element') and h['element'] != 'UNKNOWN' for h in self.simulator.hex_states):
            self.canvas.config(width=800, height=600)
            return

        # Load grid configuration for background alignment
        try:
            with open('config/grid_config.json', 'r') as f:
                grid_config = json.load(f)
        except:
            grid_config = None

        hex_radius = self.grid_manager.hex_size - 2
        padding = 20

        # Calculate bounds of the hex grid
        centers = self.grid_manager.hex_centers
        self.draw_offsets['padding'] = padding
        self.draw_offsets['x'] = min(c[0] for c in centers) - hex_radius
        self.draw_offsets['y'] = min(c[1] for c in centers) - hex_radius
        
        max_x = max(c[0] for c in centers) + hex_radius
        max_y = max(c[1] for c in centers) + hex_radius

        canvas_width = max_x - self.draw_offsets['x'] + (2 * padding)
        canvas_height = max_y - self.draw_offsets['y'] + (2 * padding)
        self.canvas.config(width=canvas_width, height=canvas_height)

        # Set background image if available
        if self.background_image and grid_config:
            try:
                # Since background image has same resolution as game (1440x900),
                # we need to crop the relevant game area and align it properly
                left_anchor = grid_config['anchor_points']['left_most_hex_center']
                right_anchor = grid_config['anchor_points']['right_most_hex_center']
                
                # Calculate the offset between background coordinates and canvas coordinates
                bg_offset_x = self.draw_offsets['x'] - padding
                bg_offset_y = self.draw_offsets['y'] - padding
                
                # Crop the background to match the canvas area
                crop_left = max(0, int(bg_offset_x))
                crop_top = max(0, int(bg_offset_y))
                crop_right = min(self.background_image.width, int(bg_offset_x + canvas_width))
                crop_bottom = min(self.background_image.height, int(bg_offset_y + canvas_height))
                
                if crop_right > crop_left and crop_bottom > crop_top:
                    bg_crop = self.background_image.crop((crop_left, crop_top, crop_right, crop_bottom))
                    
                    # Convert to PhotoImage and set as background
                    self.bg_photo = ImageTk.PhotoImage(bg_crop)
                    
                    # Position the background correctly on canvas
                    canvas_x = max(0, -bg_offset_x)
                    canvas_y = max(0, -bg_offset_y)
                    self.canvas.create_image(canvas_x, canvas_y, anchor=tk.NW, image=self.bg_photo)
            except Exception as e:
                print(f"Error setting background: {e}")

        unlocked_indices = self.simulator.get_unlocked_indices()
        
        for i, hex_data in enumerate(self.simulator.hex_states):
            center_x, center_y = centers[i]
            # Translate coordinates to fit in canvas
            draw_x = center_x - self.draw_offsets['x'] + padding
            draw_y = center_y - self.draw_offsets['y'] + padding

            element = hex_data.get("element", "UNKNOWN")
            is_unlocked = hex_data.get("unlocked", False)
            
            # Draw selection highlight
            if i == self.selected_hex_index:
                selection_radius = hex_radius + 5
                self.draw_hexagon(draw_x, draw_y, selection_radius, "", "cyan", 3)
            
            # Draw hint highlight
            if self.hinted_move and i in self.hinted_move:
                hint_radius = hex_radius + 6
                self.draw_hexagon(draw_x, draw_y, hint_radius, "", "green", 4)
            
            # Use element image if available
            state = "normal" if is_unlocked else "darkened"
            image_key = f"{element}_{state}"
            
            if image_key in self.element_images and element not in ["EMPTY", "UNKNOWN", "OUT_OF_BOUNDS"]:
                # Draw the element image
                self.canvas.create_image(draw_x, draw_y, image=self.element_images[image_key])
            elif element not in ["EMPTY", "UNKNOWN", "OUT_OF_BOUNDS"]:
                # Fallback to colored hexagon if image not available
                color_name = self.element_colors.get(element, "magenta")
                final_color = color_name if is_unlocked else self.darken_color(color_name)
                outline_color = "yellow" if is_unlocked else "white"
                outline_width = 3 if i == self.selected_hex_index else 1
                self.draw_hexagon(draw_x, draw_y, hex_radius, final_color, outline_color, outline_width)
                
                # Add text label
                text_color = "white" if is_unlocked else "gray50"
                self.canvas.create_text(draw_x, draw_y, text=element[:2], fill=text_color, font=("Arial", 8, "bold"))

    def prompt_load_puzzle(self):
        filepath = filedialog.askopenfilename(title="Select a Puzzle Recording", filetypes=(("JSON files", "*.json"), ("All files", "*.*")), initialdir="recordings")
        if filepath:
            self.load_puzzle_from_path(filepath)

    def load_puzzle_from_path(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.simulator.load_board_state(data["initial_board_state"])
            self.info_label.config(text=f"Loaded: {data.get('puzzle_name', 'Unnamed Puzzle')}")
            self.undo_button.config(state=tk.DISABLED)
            self.solve_button.config(state=tk.NORMAL)
            self.hint_button.config(state=tk.DISABLED)
            self.selected_hex_index = None
            self.solution_path = None
            self.hinted_move = None
            self.draw_board()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load puzzle: {e}")

    def on_canvas_click(self, event):
        if not self.simulator.hex_states: return
        
        # Translate canvas coordinates back to original grid coordinates
        original_x = event.x + self.draw_offsets['x'] - self.draw_offsets['padding']
        original_y = event.y + self.draw_offsets['y'] - self.draw_offsets['padding']

        clicked_index = self.grid_manager.find_closest_hex(original_x, original_y)
        
        if clicked_index is None or self.simulator.hex_states[clicked_index]["element"] == "EMPTY":
            self.selected_hex_index = None
            self.draw_board()
            return

        if clicked_index not in self.simulator.get_unlocked_indices(): return

        clicked_element = self.simulator.hex_states[clicked_index]["element"]

        # Handle GOLD elimination
        if clicked_element == "GOLD":
            if self.simulator.eliminate_single_element(clicked_index):
                self.undo_button.config(state=tk.NORMAL)
                # Any single elimination invalidates a pair-based hint.
                if self.hinted_move:
                    self.info_label.config(text="Hint invalidated by custom move.")
                    self.hinted_move = None
                    self.solution_path = None
                    self.hint_button.config(state=tk.DISABLED)
                if self.simulator.is_solved():
                    self.info_label.config(text="Puzzle Solved!")
                    messagebox.showinfo("Congratulations!", "You have solved the puzzle!")
            self.selected_hex_index = None
        # Handle normal selection/matching
        elif self.selected_hex_index is None:
            self.selected_hex_index = clicked_index
        elif self.selected_hex_index == clicked_index:
            self.selected_hex_index = None
        else:
            if self.simulator.attempt_move(self.selected_hex_index, clicked_index):
                self.undo_button.config(state=tk.NORMAL)
                
                # Check if the move followed the hint or invalidated it.
                if self.hinted_move:
                    move = tuple(sorted((self.selected_hex_index, clicked_index)))
                    if move == self.hinted_move:
                        self.hinted_move = None # Followed hint, clear green box for next hint
                    else:
                        self.info_label.config(text="Hint invalidated by custom move.")
                        self.hinted_move = None
                        self.solution_path = None
                        self.hint_button.config(state=tk.DISABLED)

                if self.simulator.is_solved():
                    self.info_label.config(text="Puzzle Solved!")
                    messagebox.showinfo("Congratulations!", "You have solved the puzzle!")
            self.selected_hex_index = None
        
        self.draw_board()

    def undo_move(self):
        if self.simulator.undo_move():
            self.info_label.config(text="Move undone.")
            self.hinted_move = None # Clear hint on undo
            self.solution_path = None
            self.hint_button.config(state=tk.DISABLED)
            self.solve_button.config(state=tk.NORMAL)
            self.draw_board()
            if not self.simulator.move_history:
                self.undo_button.config(state=tk.DISABLED)

    def solve_puzzle(self):
        """Starts the puzzle-solving process in a separate thread."""
        if self.solving_thread and self.solving_thread.is_alive():
            self.info_label.config(text="Solver is already running.")
            return

        self.info_label.config(text="Solving...")
        self.solve_button.config(state=tk.DISABLED)
        self.hint_button.config(state=tk.DISABLED)
        self.load_button.config(state=tk.DISABLED)
        self.undo_button.config(state=tk.DISABLED)
        self.master.update_idletasks()

        current_board = self.simulator.get_current_game_board()
        
        self.solving_thread = threading.Thread(
            target=self._solve_worker,
            args=(current_board,)
        )
        self.solving_thread.start()
        self.master.after(100, self._check_solve_result)

    def _solve_worker(self, board_to_solve):
        """Runs the solver in a background thread and puts the result in a queue."""
        solution = self.solver.solve(board_to_solve)
        self.result_queue.put(solution)

    def _check_solve_result(self):
        """Checks the queue for a result from the solver thread."""
        try:
            solution = self.result_queue.get_nowait()
            
            # Re-enable buttons now that the process is complete
            self.solve_button.config(state=tk.NORMAL)
            self.load_button.config(state=tk.NORMAL)
            self.undo_button.config(state=tk.NORMAL if self.simulator.move_history else tk.DISABLED)

            if solution:
                self.solution_path = solution
                self.info_label.config(text=f"Solution found in {len(solution)} moves! Click Hint.")
                self.hint_button.config(state=tk.NORMAL)
            else:
                self.info_label.config(text="No solution found from this state.")

        except queue.Empty:
            # If no result yet, check again after 100ms
            self.master.after(100, self._check_solve_result)

    def show_next_move_hint(self):
        # If a hint is already shown, execute it on the second click.
        if self.hinted_move:
            idx1, idx2 = self.hinted_move
            
            # Check if the move is still valid before attempting
            if self.simulator.hex_states[idx1]["element"] != "EMPTY" and \
               self.simulator.hex_states[idx2]["element"] != "EMPTY":
                
                if self.simulator.attempt_move(idx1, idx2):
                    self.undo_button.config(state=tk.NORMAL)
                    if self.simulator.is_solved():
                        self.info_label.config(text="Puzzle Solved!")
                        messagebox.showinfo("Congratulations!", "You have solved the puzzle!")
                
            self.hinted_move = None # Clear hint after execution
            self.draw_board()
            
            # Check if there are more steps in the solution
            if not self.solution_path:
                self.hint_button.config(state=tk.DISABLED)
                self.info_label.config(text="End of solution path.")
            return

        # If no hint is shown, get the next one from the solution path.
        if self.solution_path:
            self.hinted_move = self.solution_path.pop(0)
            self.draw_board()
            self.info_label.config(text="Hint shown. Click again to execute or make your own move.")

def capture_current_game_state():
    """Captures the current game state from the screen and returns the board state."""
    print("Capturing game window...")
    wm = WindowManager()
    gm = GridManager()
    ed = ElementDetector()
    
    wm.focus()
    time.sleep(0.2)
    screenshot = wm.capture()
    
    if screenshot is None:
        print("Error: Failed to capture screen.")
        return None
        
    print("Analyzing board elements...")
    identified_elements = ed.identify_elements(screenshot, gm)
    return identified_elements

def main():
    parser = argparse.ArgumentParser(description="Opus Magnum Puzzle Recorder & Simulator.")
    subparsers = parser.add_subparsers(dest='mode', help='Available modes')

    # Capture mode
    parser_capture = subparsers.add_parser('capture', help='Capture the current board state from the game.')
    parser_capture.add_argument('output', nargs='?', default=None, help='Optional. Path to save the recording file.')

    # Simulate mode
    parser_simulate = subparsers.add_parser('simulate', help='Run the puzzle simulator GUI.')
    parser_simulate.add_argument('input', nargs='?', default=None, help='Optional. Path to a recording file to load.')

    args = parser.parse_args()

    if args.mode == 'capture':
        board_state = capture_current_game_state()
        if board_state:
            recorder = PuzzleRecorder()
            recorder.record(board_state, [], puzzle_name=args.output)
    elif args.mode == 'simulate':
        root = tk.Tk()
        app = PuzzleReplayGUI(root)
        if args.input:
            app.load_puzzle_from_path(args.input)
        root.mainloop()
    else:
        # Default behavior
        print("No mode specified. Defaulting to capture and simulate.")
        board_state = capture_current_game_state()
        if board_state:
            recorder = PuzzleRecorder()
            # Save to a temporary file
            temp_path = recorder.record(board_state, [], puzzle_name="temp_capture")
            if temp_path:
                root = tk.Tk()
                app = PuzzleReplayGUI(root)
                app.load_puzzle_from_path(temp_path)
                root.mainloop()

if __name__ == "__main__":
    main()