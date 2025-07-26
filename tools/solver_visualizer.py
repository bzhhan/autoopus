import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import os

class SolverVisualizer:
    """
    Visualizes the A* solver's search process by generating a final graph.
    """
    def __init__(self):
        """
        Initializes the visualizer.
        """
        self.graph = nx.DiGraph()
        self.node_colors = {}
        self.node_labels = {}
        self.solution_path_hashes = []
        self.input_filepath = None
        self.no_display = False

        # Node status constants
        self.STATUS_CLOSED = 'lightgray'
        self.STATUS_SOLUTION = 'red'
        self.STATUS_INITIAL = 'limegreen'

    def add_node(self, node_hash, parent_hash=None, g_cost=0, h_cost=0, is_initial=False):
        """Adds a node and its relationship to the graph data."""
        f_cost = g_cost + h_cost
        if node_hash not in self.graph:
            self.graph.add_node(node_hash, g=g_cost, h=h_cost, f=f_cost)
            self.node_labels[node_hash] = f"g={g_cost}\nh={h_cost:.1f}"
            if is_initial:
                self.node_colors[node_hash] = self.STATUS_INITIAL
            else:
                self.node_colors[node_hash] = self.STATUS_CLOSED # All visited nodes are 'closed'

        if parent_hash and parent_hash in self.graph:
            self.graph.add_edge(parent_hash, node_hash, f_cost=f_cost)

    def set_solution_path(self, path_hashes):
        """Stores the solution path for final highlighting."""
        self.solution_path_hashes = path_hashes

    def _hierarchy_pos(self, G, root=None, width=1., vert_gap=0.2, vert_loc=0, xcenter=0.5):
        """
        Create a hierarchical layout for the graph.
        If the graph is a tree this will return the positions to plot this in a
        hierarchical layout.
        """
        if not nx.is_tree(G):
            # If not a tree, use spring layout as fallback
            return nx.spring_layout(G)
        
        if root is None:
            if isinstance(G, nx.DiGraph):
                root = next(iter(nx.topological_sort(G)))  # allows back compatibility with nx version 1.11
            else:
                root = list(G.nodes)[0]

        def _hierarchy_pos_recursive(G, root, width=1., vert_gap=0.2, vert_loc=0, xcenter=0.5, pos=None, parent=None, parsed=[]):
            if pos is None:
                pos = {root: (xcenter, vert_loc)}
            else:
                pos[root] = (xcenter, vert_loc)
            children = list(G.neighbors(root))
            if not isinstance(G, nx.DiGraph) and parent is not None:
                children.remove(parent)
            if len(children) != 0:
                dx = width/len(children)
                nextx = xcenter - width/2 - dx/2
                for child in children:
                    nextx += dx
                    pos = _hierarchy_pos_recursive(G, child, width=dx, vert_gap=vert_gap,
                                                  vert_loc=vert_loc-vert_gap, xcenter=nextx,
                                                  pos=pos, parent=root, parsed=parsed)
            return pos

        return _hierarchy_pos_recursive(G, root, width, vert_gap, vert_loc, xcenter)

    def generate_layout_and_draw(self):
        """
        Calculates the layout and draws the final graph.
        This should be called once after the solver finishes.
        """
        if not self.graph:
            print("Visualizer: Graph is empty, nothing to draw.")
            return

        print("Visualizer: Generating graph layout...")
        # Use a layout that works well for tree-like structures
        try:
            # pydot layout is best for hierarchical graphs, but requires graphviz
            pos = nx.nx_agraph.graphviz_layout(self.graph, prog='dot')
        except ImportError:
            print("Visualizer: `pygraphviz` not found. Falling back to custom hierarchy layout.")
            pos = self._hierarchy_pos(self.graph)

        fig, ax = plt.subplots(figsize=(20, 20))
        
        # Highlight the solution path
        for node_hash in self.solution_path_hashes:
            if node_hash in self.graph:
                self.node_colors[node_hash] = self.STATUS_SOLUTION
        
        colors = [self.node_colors.get(node, self.STATUS_CLOSED) for node in self.graph.nodes()]
        
        # --- Edge coloring based on f_cost ---
        edges = self.graph.edges(data=True)
        f_costs = [data.get('f_cost', 0) for _, _, data in edges]
        
        edge_colors = 'gray' # Default
        if f_costs:
            min_f = min(f_costs)
            max_f = max(f_costs)
            f_range = max_f - min_f
            
            normalized_f = []
            if f_range > 0:
                normalized_f = [(cost - min_f) / f_range for cost in f_costs]
            else: # All costs are the same
                normalized_f = [0.5] * len(f_costs)

            cmap = plt.get_cmap('viridis_r')
            edge_colors = [cmap(norm_f) for norm_f in normalized_f]

        print("Visualizer: Drawing graph...")
        nx.draw(self.graph, pos, ax=ax,
                with_labels=False,
                node_size=5,
                node_color=colors,
                edge_color=edge_colors,
                width=0.5,
                alpha=0.8,
                arrows=True)
        
        # nx.draw_networkx_labels(self.graph, pos, labels=self.node_labels, font_size=6, ax=ax)

        ax.set_title(f"A* Search Space (Nodes: {len(self.graph.nodes())})")
        plt.tight_layout()
        
        # Save the figure
        if self.input_filepath:
            output_filename = f"visualization_{os.path.splitext(os.path.basename(self.input_filepath))[0]}.png"
            plt.savefig(output_filename, dpi=300, bbox_inches='tight')
            print(f"Visualizer: Graph saved to {output_filename}")
        else:
            print("Visualizer: Input filepath not set, skipping save.")


        if not self.no_display:
            print("Visualizer: Displaying graph. Close the plot window to exit.")
            plt.show()

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
