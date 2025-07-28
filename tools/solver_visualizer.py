import os
from PIL import Image, ImageDraw


Image.MAX_IMAGE_PIXELS = None

class SolverVisualizer:
    """
    Visualizes the A* solver's search process by incrementally drawing to an image.
    This avoids high memory consumption and performance issues with large graphs.
    """
    def __init__(self, width=800, height=800):
        """
        Initializes the visualizer with a starting canvas size.
        The canvas will expand dynamically as needed.
        """
        # --- Configuration ---
        self.h_gap = 0.04
        self.v_gap = 80
        self.node_radius = 1
        self.save_interval = 100000
        self.output_filename = "visualization_in_progress.png"
        self.padding = 20

        # --- State and Data Structures ---
        self.image = Image.new('RGBA', (width, height), (255, 255, 255, 255))
        self.draw = ImageDraw.Draw(self.image)
        self.node_positions = {}  # {node_hash: (x, y)}
        self.level_max_x = {}     # {y_level: max_x}
        self.nodes_to_draw_buffer = []
        self.solution_path_hashes = [] # The ordered list of hashes
        self.solution_path_set = set() # For fast lookups
        self.nodes_processed_since_save = 0
        self.input_filepath = None
        self.no_display = False # Kept for compatibility, but display is now file-based
        self.global_min_f = float('inf')
        self.global_max_f = float('-inf')

        # --- Colors ---
        self.COLOR_SOLUTION = (252, 78, 42, 255) # Viridis-like Red/Orange for high visibility
        self.COLOR_INITIAL = (0, 200, 0, 255)     # Green
        self.COLOR_EDGE = (180, 180, 180, 50)    # Gray with low alpha
        # Full Viridis colormap (256 colors)
        self.VIRIDIS_MAP = [
            (68, 1, 84), (69, 11, 92), (70, 21, 99), (71, 30, 107), (72, 39, 113),
            (72, 48, 119), (72, 56, 124), (72, 65, 128), (71, 73, 132), (70, 81, 135),
            (68, 89, 138), (66, 97, 140), (64, 105, 141), (61, 113, 142), (58, 121, 142),
            (55, 128, 142), (52, 136, 142), (49, 143, 141), (46, 150, 140), (43, 158, 138),
            (41, 165, 136), (39, 172, 133), (39, 180, 129), (42, 187, 125), (49, 194, 120),
            (58, 201, 114), (70, 208, 107), (84, 214, 99), (100, 221, 89), (118, 227, 79),
            (137, 233, 67), (158, 239, 54), (179, 244, 43), (201, 248, 36), (223, 252, 34),
            (240, 255, 33), (253, 231, 37) # Truncated for example, a full map has 256 entries
        ]

    def add_node(self, node_hash, parent_hash=None, g_cost=0, h_cost=0, is_initial=False):
        """
        Calculates node position and adds it to a buffer for drawing.
        """
        # 1. Calculate Y coordinate based on depth (g_cost)
        y = self.padding + g_cost * self.v_gap

        # 2. Calculate X coordinate to prevent overlaps
        if is_initial:
            x = self.image.width // 2
        else:
            parent_x, _ = self.node_positions.get(parent_hash, (self.image.width // 2, self.padding))
            last_x_on_level = self.level_max_x.get(y, 0)
            x = max(parent_x, last_x_on_level + self.h_gap)

        # 3. Update the rightmost coordinate for this level and store position
        self.level_max_x[y] = x
        self.node_positions[node_hash] = (x, y)

        # 4. Add to Buffer
        parent_pos = self.node_positions.get(parent_hash)
        f_cost = g_cost + h_cost
        if f_cost != float('inf'):
            self.global_min_f = min(self.global_min_f, f_cost)
            self.global_max_f = max(self.global_max_f, f_cost)
        self.nodes_to_draw_buffer.append(((x, y), parent_pos, f_cost, is_initial))
        self.nodes_processed_since_save += 1

        # 4. Periodic Save
        if self.nodes_processed_since_save >= self.save_interval:
            self.draw_and_save(is_final=False)

    def set_solution_path(self, path_hashes):
        """Stores the solution path for final highlighting."""
        self.solution_path_hashes = path_hashes # Keep the ordered list
        self.solution_path_set = set(path_hashes)    # Create a set for fast lookups

    def adapt_h_gap_from_filename(self, filepath):
        """
        Adapts the horizontal gap based on the time mentioned in the filename
        to keep the visual width of graphs relatively consistent.
        """
        if not filepath:
            return

        import re
        
        base_name = os.path.basename(filepath)
        match = re.search(r'_(\d+)s_', base_name)
        
        if match:
            try:
                time_in_seconds = int(match.group(1))
                # Target product: 68s * 0.04 h_gap = 2.72
                target_product = 1.6
                if time_in_seconds > 0:
                    self.h_gap = target_product / time_in_seconds
                    print(f"Visualizer: Adapted h_gap to {self.h_gap:.4f} based on filename ({time_in_seconds}s).")
                else:
                    # Handle case of 0s to avoid division by zero
                    self.h_gap = 0.1 # Assign a large gap for 0s puzzles
                    print(f"Visualizer: Set h_gap to {self.h_gap:.4f} for 0s puzzle.")

            except (ValueError, IndexError):
                print("Visualizer: Could not parse time from filename, using default h_gap.")
        else:
            print("Visualizer: No time info in filename, using default h_gap.")


    def _expand_canvas_if_needed(self, max_x, max_y):
        """Checks if the canvas needs to be expanded and does so if necessary."""
        current_width, current_height = self.image.size
        needs_expand = False
        new_width = current_width
        new_height = current_height

        if max_x >= current_width:
            new_width = int(max_x * 1.5)
            needs_expand = True
        if max_y >= current_height:
            new_height = int(max_y * 1.5)
            needs_expand = True

        if needs_expand:
            print(f"Visualizer: Expanding canvas from {current_width}x{current_height} to {new_width}x{new_height}")
            new_image = Image.new('RGBA', (new_width, new_height), (255, 255, 255, 255))
            new_image.paste(self.image, (0, 0), self.image) # Paste with alpha channel
            self.image = new_image
            self.draw = ImageDraw.Draw(self.image)

    def draw_and_save(self, is_final=False):
        """
        Draws all nodes from the buffer onto the canvas and saves the image.
        """
        if not self.nodes_to_draw_buffer:
            return
            
        # Check required canvas size before drawing
        max_x = 0
        max_y = 0
        for pos, parent_pos, f_cost, is_initial in self.nodes_to_draw_buffer:
            max_x = max(max_x, pos[0])
            max_y = max(max_y, pos[1])
        self._expand_canvas_if_needed(max_x + self.padding, max_y + self.padding)

        # --- F-Cost Color Mapping ---
        f_range = self.global_max_f - self.global_min_f if self.global_max_f > self.global_min_f else 1.0

        def get_viridis_color(value, min_val, val_range):
            # A more complete viridis map would be better. This is a simplified version.
            if val_range <= 0:
                return self.VIRIDIS_MAP[0]
            norm = max(0, min(1, (value - min_val) / val_range))
            # Using a simple 2-color interpolation for robustness
            # Blue (low) to Yellow (high) part of Viridis
            start_color = (68, 1, 84)
            end_color = (253, 231, 37)
            r = int(start_color[0] + norm * (end_color[0] - start_color[0]))
            g = int(start_color[1] + norm * (end_color[1] - start_color[1]))
            b = int(start_color[2] + norm * (end_color[2] - start_color[2]))
            return (r, g, b)

        print(f"Visualizer: Drawing {len(self.nodes_to_draw_buffer)} new nodes...")
        
        # Create a single transparent layer for all edges in this batch
        edge_layer = Image.new('RGBA', self.image.size, (0, 0, 0, 0))
        edge_draw = ImageDraw.Draw(edge_layer)

        for pos, parent_pos, f_cost, is_initial in self.nodes_to_draw_buffer:
            if parent_pos:
                edge_draw.line([(int(parent_pos[0]), int(parent_pos[1])), (int(pos[0]), int(pos[1]))], fill=self.COLOR_EDGE, width=1)

        # Composite the edge layer once
        self.image.alpha_composite(edge_layer)
        
        # Now draw the nodes on top
        for pos, parent_pos, f_cost, is_initial in self.nodes_to_draw_buffer:
            if is_initial:
                node_color = self.COLOR_INITIAL
            else:
                node_color = get_viridis_color(f_cost, self.global_min_f, f_range)

            self.draw.ellipse(
                [int(pos[0])-self.node_radius, int(pos[1])-self.node_radius,
                 int(pos[0])+self.node_radius, int(pos[1])+self.node_radius],
                fill=node_color
            )
        
        # Clear the buffer
        self.nodes_to_draw_buffer = []
        self.nodes_processed_since_save = 0

        # If it's the final draw, highlight the solution path
        if is_final and self.solution_path_hashes:
            print("Visualizer: Highlighting solution path...")
            # Use the ordered list directly
            path_nodes = self.solution_path_hashes
            
            for i in range(len(path_nodes) - 1):
                start_node_hash = path_nodes[i]
                end_node_hash = path_nodes[i+1]
                
                # Check if both nodes were actually drawn
                if start_node_hash not in self.node_positions or end_node_hash not in self.node_positions:
                    continue
                
                start_pos = self.node_positions[start_node_hash]
                end_pos = self.node_positions[end_node_hash]

                # Redraw edge in solution color
                self.draw.line([(int(start_pos[0]), int(start_pos[1])), (int(end_pos[0]), int(end_pos[1]))], fill=self.COLOR_SOLUTION, width=1)
                # Redraw node in solution color
                self.draw.ellipse(
                    [int(start_pos[0])-self.node_radius, int(start_pos[1])-self.node_radius,
                     int(start_pos[0])+self.node_radius, int(start_pos[1])+self.node_radius],
                    fill=self.COLOR_SOLUTION
                )
            # Draw the final node of the path
            if path_nodes:
                final_node_pos = self.node_positions[path_nodes[-1]]
                self.draw.ellipse(
                    [int(final_node_pos[0])-self.node_radius, int(final_node_pos[1])-self.node_radius,
                     int(final_node_pos[0])+self.node_radius, int(final_node_pos[1])+self.node_radius],
                    fill=self.COLOR_SOLUTION
                )


        # Determine filename
        if self.input_filepath:
            base_name = os.path.splitext(os.path.basename(self.input_filepath))[0]
            self.output_filename = f"visualization_{base_name}.png"
        
        print(f"Visualizer: Saving full-resolution image to {self.output_filename}...")
        self.image.save(self.output_filename)
        print("Visualizer: Full-resolution save complete.")

        # --- Create and save a downsampled version for easy viewing ---
        max_preview_size = 16000
        if self.image.width > max_preview_size or self.image.height > max_preview_size:
            try:
                preview_image = self.image.copy()
                preview_image.thumbnail((max_preview_size, max_preview_size), Image.Resampling.LANCZOS)
                
                base, ext = os.path.splitext(self.output_filename)
                preview_filename = f"{base}_preview.png"
                
                print(f"Visualizer: Saving downsampled preview to {preview_filename}...")
                # If original was RGBA, convert to RGB for saving as PNG without alpha issues
                if preview_image.mode == 'RGBA':
                    preview_image = preview_image.convert('RGB')
                preview_image.save(preview_filename)
                print("Visualizer: Preview save complete.")
            except Exception as e:
                print(f"Visualizer: Could not create or save preview image. Error: {e}")

    def generate_layout_and_draw(self):
        """
        This is now just a wrapper for the final save operation.
        """
        print("Visualizer: Finalizing visualization...")
        self.draw_and_save(is_final=True)

if __name__ == '__main__':
    import argparse
    import json
    import sys
    import os
    
    # Add the project root to the Python path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from src.grid_manager import GridManager
    from src.solver import Solver, GameBoard

    parser = argparse.ArgumentParser(description="Run the A* solver with visualization on a recorded puzzle file.")
    parser.add_argument("filepath", type=str, help="Path to the puzzle JSON file recorded by puzzle_recorder.py")
    parser.add_argument("--no-display", action="store_true", help="Do not display the plot window, just save the file.")
    args = parser.parse_args()

    try:
        with open(args.filepath, 'r') as f:
            data = json.load(f)
        
        identified_elements = data['initial_board_state']
        
        print("Initializing components...")
        gm = GridManager()
        board = GameBoard(gm)
        board.update_board_state(identified_elements)
        
        visualizer = SolverVisualizer()
        visualizer.adapt_h_gap_from_filename(args.filepath) # Adapt h_gap
        solver = Solver(visualizer=visualizer)
        visualizer.input_filepath = args.filepath
        visualizer.no_display = args.no_display
        
        print("Starting solver with visualization...")
        solution_path = solver.solve(board)
        
        if solution_path:
            print("\nSolution found!")
        else:
            print("\nNo solution found.")
            
    except FileNotFoundError:
        print(f"Error: The file '{args.filepath}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from the file '{args.filepath}'.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
