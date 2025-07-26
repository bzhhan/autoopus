import copy
import heapq
import time
import json
import operator

class GameBoard:
    """
    Represents the state of the game board. Now includes hashing for A* visited set.
    """
    def __init__(self, grid_manager):
        self.grid = grid_manager
        self.hex_states = [{"element": "UNKNOWN", "state": "normal"}] * len(self.grid.hex_centers)
        self.metal_transmutation_order = ["LEAD", "TIN", "IRON", "COPPER", "SILVER", "GOLD"]
        self._hash = None

    def update_board_state(self, identified_elements):
        if len(identified_elements) != len(self.hex_states):
            raise ValueError("Mismatch between identified elements and board size.")
        self.hex_states = identified_elements
        self._update_unlock_status()

    def _update_unlock_status(self):
        
        for i, hex_info in enumerate(self.hex_states):
            if hex_info["element"] in ["EMPTY", "OUT_OF_BOUNDS", "UNKNOWN"]:
                self.hex_states[i]['unlocked'] = True
                continue

            
            neighbor_indices = self.grid.neighbors[i]
            
            
            # 创建一个表示邻居是否为空的列表
            # 关键点：对于边界外的位置(索引为-1)，视为空白
            neighbor_is_empty = []
            for neighbor_idx in neighbor_indices:
                # 如果邻居索引是-1(边界外)或者邻居是空的，则为True
                if neighbor_idx == -1:
                    neighbor_is_empty.append(True)  # 边界外视为空
                elif self.hex_states[neighbor_idx]["element"] == "EMPTY":
                    neighbor_is_empty.append(True)  # 实际空格
                else:
                    neighbor_is_empty.append(False)
            
            
            
            # 检查是否有三个连续的空邻居(循环检查)
            # 将数组复制并扩展，以便我们可以循环检查
            is_empty_circular = neighbor_is_empty + neighbor_is_empty[:2]
            is_unlocked = False
            
            for j in range(len(neighbor_is_empty)):
                if all(is_empty_circular[j:j+3]):  # 检查连续的3个空位
                    is_unlocked = True
                    break
            
            self.hex_states[i]['unlocked'] = is_unlocked
            

    def find_possible_moves(self):
        
        self._update_unlock_status()
        unlocked_hexes = [i for i, h in enumerate(self.hex_states) if h.get('unlocked', False)]
        

        possible_moves = []
        for i in range(len(unlocked_hexes)):
            for j in range(i + 1, len(unlocked_hexes)):
                idx1, idx2 = unlocked_hexes[i], unlocked_hexes[j]
                if self._is_valid_match(idx1, idx2):
                    possible_moves.append(tuple(sorted((idx1, idx2))))
        
        
        return possible_moves

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
        """
        Checks if the given metal is the lowest-ranking metal currently on the board.
        """
        current_metals_on_board = {h["element"] for h in self.hex_states if h["element"] in self.metal_transmutation_order}
        
        lowest_metal_on_board = next((metal for metal in self.metal_transmutation_order if metal in current_metals_on_board), None)
        
        return metal_element == lowest_metal_on_board

    def apply_move(self, move):
        new_board = copy.deepcopy(self)
        idx1, idx2 = move
        new_board.hex_states[idx1] = {"element": "EMPTY", "state": "normal", "unlocked": False}
        new_board.hex_states[idx2] = {"element": "EMPTY", "state": "normal", "unlocked": False}
        new_board._update_unlock_status()
        new_board._hash = None # CRITICAL: Invalidate the hash cache
        return new_board

    def is_solved(self):
        """
        Checks if the board is solved. A board is solved if it is either
        completely empty, or the only remaining element is a single GOLD marble.
        """
        remaining_elements = [h['element'] for h in self.hex_states if h['element'] not in ["EMPTY", "OUT_OF_BOUNDS", "UNKNOWN"]]
        
        # Condition 1: Board is completely empty
        if not remaining_elements:
            return True
            
        # Condition 2: Only a single GOLD marble remains
        if len(remaining_elements) == 1 and remaining_elements[0] == "GOLD":
            return True
            
        return False

    def __lt__(self, other):
        # Allows GameBoard objects to be compared in the priority queue
        return False

    def __hash__(self):
        if self._hash is None:
            # Create a tuple of tuples of sorted dict items for a stable hash
            self._hash = hash(tuple(tuple(sorted(d.items())) for d in self.hex_states))
        return self._hash

    def __eq__(self, other):
        return isinstance(other, GameBoard) and self.__hash__() == other.__hash__()

class Solver:
    """
    Solves the puzzle using the A* search algorithm.
    """
    def __init__(self, overlay_manager=None, heuristic_weights=None, visualizer=None):
        """
        Initializes the Solver.

        Args:
            overlay_manager (OverlayManager, optional): Manager for the GUI overlay.
            heuristic_weights (dict, optional): A dictionary of weights for the heuristic function.
                                                If not provided, it's loaded from config.
            visualizer (SolverVisualizer, optional): Visualizer for the A* search process.
        """
        self.overlay_manager = overlay_manager
        self.visualizer = visualizer
        self._load_interrupt_config()
        if heuristic_weights:
            self.h_weights = heuristic_weights
        else:
            self._load_heuristic_weights()

    def _load_heuristic_weights(self):
        """Loads the heuristic weights from the config file."""
        # Set default values first
        self.h_weights = {
            "remaining_elements_factor": 0.5,
            "locked_marbles_penalty": 0.1,
            "salt_marbles_reward": 1.0,
            "metal_marbles_penalty": 1.5
        }
        try:
            with open("config/solver_config.json", 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Overwrite defaults with values from config if they exist
                self.h_weights.update(config.get('heuristic_weights', {}))
        except (FileNotFoundError, json.JSONDecodeError) as e:
            msg = f"Warning: Could not load solver_config.json: {e}. Using default weights."
            if self.overlay_manager:
                self.overlay_manager.log(msg)
            else:
                print(f"\n{msg}")

    def _load_interrupt_config(self):
        """Loads the interrupt conditions from the config file."""
        self.interrupt_config = {"enabled": False}
        try:
            with open("config/interrupt_config.json", 'r', encoding='utf-8') as f:
                self.interrupt_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            if self.overlay_manager:
                self.overlay_manager.log(f"Warning: Could not load interrupt config: {e}")
            else:
                print(f"\nWarning: Could not load interrupt config: {e}")

    def _evaluate_conditions(self, condition_set, values):
        """
        Recursively evaluates a set of conditions.

        Args:
            condition_set (dict): The condition set from the config.
            values (dict): A dictionary of current solver state values.

        Returns:
            bool: True if the conditions are met, False otherwise.
        """
        ops = {
            ">": operator.gt, "<": operator.lt,
            "==": operator.eq, "!=": operator.ne,
            ">=": operator.ge, "<=": operator.le
        }

        results = []
        for condition in condition_set['conditions']:
            # If it's a nested group, recurse
            if 'logic' in condition:
                results.append(self._evaluate_conditions(condition, values))
            # Otherwise, it's a single condition
            else:
                var = condition['variable']
                op = condition['operator']
                val = condition['value']
                
                if var in values and op in ops:
                    result = ops[op](values[var], val)
                    results.append(result)
                else:
                    results.append(False) # Variable or operator not found

        if condition_set['logic'].upper() == 'AND':
            return all(results)
        elif condition_set['logic'].upper() == 'OR':
            return any(results)
        return False

    def _check_interrupt(self, iteration, open_set_size, best_g_cost, elapsed_time):
        """Checks if the solver should be interrupted based on config."""
        if not self.interrupt_config.get("enabled", False):
            return False

        values = {
            "iteration": iteration,
            "open_set_size": open_set_size,
            "best_g_cost": best_g_cost,
            "elapsed_time": elapsed_time
        }

        if self._evaluate_conditions(self.interrupt_config['condition_set'], values):
            msg = "Solver interrupted by user-defined condition."
            if self.overlay_manager:
                self.overlay_manager.log(msg)
            else:
                print(f"\n{msg}")
            return True
        return False

    def solve(self, initial_board):
        """
        Starts the A* search for a solution.
        
        Args:
            initial_board (GameBoard): The starting state of the board.

        Returns:
            list: The list of moves if a solution is found, otherwise None.
        """

        
        # Priority queue: (f_cost, g_cost, board_state, path, parent_board)
        open_set = [(0, 0, initial_board, [], None)]
        heapq.heapify(open_set)
        
        # Visited set stores hashes of boards we've already evaluated
        closed_set = set()
        
        # Track parent relationships for visualization
        parent_map = {}

        start_time = time.time()
        iteration = 0
        
        # Add initial node to visualizer if available
        if self.visualizer:
            self.visualizer.add_node(hash(initial_board), parent_hash=None, g_cost=0, h_cost=0, is_initial=True)
        
        while open_set:
            iteration += 1
            
            # --- Progress Bar Logic ---
            elapsed_time = time.time() - start_time
            # We need to get g_cost before popping, so we peek at the best item
            if open_set:
                best_g_cost = open_set[0][1]
            else:
                best_g_cost = 0 # Should not happen if loop continues

            progress_str = (
                f"S... [ I: {iteration:5d} | "
                f"Q: {len(open_set):4d} | "
                f"P: {best_g_cost:2d} | "
                f"T: {elapsed_time:5.1f}s ]"
            )
            if self.overlay_manager:
                # On the first iteration, add a new line. On subsequent iterations, update it.
                if iteration == 1:
                    self.overlay_manager.log(progress_str)
                else:
                    self.overlay_manager.update_last_line(progress_str)
            else:
                print(f"\r{progress_str}", end="", flush=True)
            # --- End Progress Bar ---

            # --- Interrupt Check ---
            if self._check_interrupt(iteration, len(open_set), best_g_cost, elapsed_time):
                return None # Return None as no solution was found
            # --- End Interrupt Check ---

            _, g_cost, current_board, path, parent_board = heapq.heappop(open_set)

            if current_board in closed_set:
                continue
            closed_set.add(current_board)
            
            # Add node to visualizer when it's actually visited
            if self.visualizer and current_board != initial_board:
                parent_hash = hash(parent_board) if parent_board else None
                # Calculate heuristic for current board
                remaining_elements = [h for h in current_board.hex_states if h['element'] not in ["EMPTY", "OUT_OF_BOUNDS", "UNKNOWN"]]
                locked_marbles = sum(1 for h in remaining_elements if not h.get('unlocked', False))
                salt_marbles = sum(1 for h in remaining_elements if h['element'] == 'SALT')
                metal_marbles = sum(1 for h in remaining_elements if h['element'] in current_board.metal_transmutation_order or h['element'] == 'QUICKSILVER')
                h_cost = (
                    (len(remaining_elements) * self.h_weights['remaining_elements_factor']) +
                    (locked_marbles * self.h_weights['locked_marbles_penalty']) -
                    (salt_marbles * self.h_weights['salt_marbles_reward']) +
                    (metal_marbles * self.h_weights['metal_marbles_penalty'])
                )
                self.visualizer.add_node(hash(current_board), parent_hash=parent_hash, g_cost=g_cost, h_cost=h_cost)


            if current_board.is_solved():
                final_msg = "Solution found!"
                if self.overlay_manager:
                    self.overlay_manager.log(final_msg)
                else:
                    print() # Print a newline to not overwrite the final progress bar
                    print(f"DEBUG: {final_msg}", flush=True)
                
                # Set solution path in visualizer if available
                if self.visualizer:
                    # Convert path to board hashes for visualization
                    solution_hashes = [hash(initial_board)]
                    current_board_for_path = initial_board
                    for move in path:
                        current_board_for_path = current_board_for_path.apply_move(move)
                        solution_hashes.append(hash(current_board_for_path))
                    self.visualizer.set_solution_path(solution_hashes)
                    self.visualizer.generate_layout_and_draw()
                
                return path # Solution found

            possible_moves = current_board.find_possible_moves()
            for move in possible_moves:
                next_board = current_board.apply_move(move)
                if next_board in closed_set:
                    continue

                # --- Heuristic v2.1 ---
                remaining_elements = [h for h in next_board.hex_states if h['element'] not in ["EMPTY", "OUT_OF_BOUNDS", "UNKNOWN"]]
                
                locked_marbles = sum(1 for h in remaining_elements if not h.get('unlocked', False))
                salt_marbles = sum(1 for h in remaining_elements if h['element'] == 'SALT')
                metal_marbles = sum(1 for h in remaining_elements if h['element'] in next_board.metal_transmutation_order or h['element'] == 'QUICKSILVER')

                h_cost = (
                    (len(remaining_elements) * self.h_weights['remaining_elements_factor']) +
                    (locked_marbles * self.h_weights['locked_marbles_penalty']) -
                    (salt_marbles * self.h_weights['salt_marbles_reward']) +
                    (metal_marbles * self.h_weights['metal_marbles_penalty'])
                )
                # --- End Heuristic ---
                new_g_cost = g_cost + 1
                f_cost = new_g_cost + h_cost
                
                new_path = path + [move]
                heapq.heappush(open_set, (f_cost, new_g_cost, next_board, new_path, current_board))
        
        final_msg = "No solution found."
        if self.overlay_manager:
            self.overlay_manager.log(final_msg)
        else:
            print() # Print a newline to not overwrite the final progress bar
        
        # Generate visualization even if no solution found
        if self.visualizer:
            self.visualizer.generate_layout_and_draw()
        
        return None # No solution found


def _run_logic_test():
    """Runs a standalone test of the solver logic with a predefined board."""
    print("--- Running Standalone Solver Logic Test ---", flush=True)
    try:
        # 1. Initialize GridManager (needed for geometry)
        print("Step 1: Initializing GridManager...", flush=True)
        from src.grid_manager import GridManager
        grid = GridManager()
        
        # 2. Create the board with the simple test data
        print("Step 2: Creating and setting up a manual board state...", flush=True)
        initial_board = GameBoard(grid)
        
        # Create a simple, manually defined board state for testing.
        board_state = [{"element": "EMPTY", "state": "normal", "unlocked": False} for _ in range(91)]
        board_state[33] = {"element": "FIRE", "state": "normal"}
        board_state[34] = {"element": "FIRE", "state": "normal"}
        initial_board.update_board_state(board_state)
        
        # 3. Run the solver
        print("Step 3: Starting solver...", flush=True)
        solver = Solver()
        
        start_time = time.time()
        solution_path = solver.solve(initial_board)
        end_time = time.time()
        
        print(f"\nSolver finished in {end_time - start_time:.4f} seconds.", flush=True)
        
        # 4. Print the results
        print("\n--- Solver Results ---", flush=True)
        if solution_path is not None:
            print("Solution Found!", flush=True)
            print("Sequence of moves (hex indices):", flush=True)
            for i, move in enumerate(solution_path):
                print(f"  Step {i+1}: Remove hexes {move[0]} and {move[1]}", flush=True)
        else:
            print("No solution was found for this test case.", flush=True)
            print("This might indicate an issue with the unlock or matching logic.", flush=True)

    except Exception as e:
        print(f"\nAn error occurred during the logic test: {e}", flush=True)

def _run_full_test():
    """Runs the full solver test using screen capture."""
    # This test is intended to be run from the project root, e.g., `python src/solver.py`
    from src.window_manager import WindowManager
    from src.grid_manager import GridManager
    from src.element_detector import ElementDetector

    print("--- Running Full Solver Self-Test ---", flush=True)
    try:
        # 1. Initialize all components
        print("Step 1: Initializing managers...", flush=True)
        wm = WindowManager()
        grid = GridManager()
        detector = ElementDetector(match_threshold=0.6)
        
        # 2. Get the current board state
        print("Step 2: Capturing and analyzing board state...", flush=True)
        wm.focus()
        screenshot = wm.capture()
        identified_elements = detector.identify_elements(screenshot, grid)
        
        # 3. Create the initial game board
        initial_board = GameBoard(grid)
        initial_board.update_board_state(identified_elements)
        print("Board state created.", flush=True)
        
        # 4. Run the solver
        print("Step 3: Starting solver...", flush=True)
        solver = Solver() # Test without overlay
        
        start_time = time.time()
        solution_path = solver.solve(initial_board)
        end_time = time.time()
        
        # The solver prints its own progress, so add a newline
        print(f"\nSolver finished in {end_time - start_time:.4f} seconds.", flush=True)
        
        # 5. Print the results
        print("\n--- Solver Results ---", flush=True)
        if solution_path is not None:
            print("Solution Found!", flush=True)
            print("Sequence of moves (hex indices):", flush=True)
            for i, move in enumerate(solution_path):
                print(f"  Step {i+1}: Remove hexes {move[0]} and {move[1]}", flush=True)
        else:
            print("No solution was found for the current board configuration.", flush=True)

    except Exception as e:
        print(f"\nAn error occurred during the full test: {e}", flush=True)

if __name__ == '__main__':

    _run_logic_test()

    _run_full_test()
