import time
from src.window_manager import WindowManager
from src.grid_manager import GridManager

class InputManager:
    """
    Handles the execution of a solution path by translating it into a series
    of automated mouse inputs within the game window.
    """

    def __init__(self, window_manager: WindowManager, grid_manager: GridManager, overlay_manager=None):
        """
        Initializes the InputManager.

        Args:
            window_manager: An instance of WindowManager to control the game window.
            grid_manager: An instance of GridManager to get hex coordinates.
            overlay_manager (OverlayManager, optional): Manager for the GUI overlay.
        """
        self.wm = window_manager
        self.gm = grid_manager
        self.overlay_manager = overlay_manager

    def execute_solution(self, solution_path, move_duration=0.01, click_delay=0.01):
        """
        Executes the given solution path by clicking on the hex pairs.

        Args:
            solution_path (list): A list of tuples, where each tuple is a pair
                                  of hex indices to be removed.
            move_duration (float): The time in seconds for the mouse to move to a hex.
            click_delay (float): The time in seconds to wait between clicks.
        """
        self._log("\n--- Solution Execution ---")
        if not solution_path:
            self._log("Solution path is empty. Nothing to execute.")
            return

        # --- Execution Start ---
        self._log("Solution found! Starting execution...")
        #time.sleep(3)

        self.wm.focus()

        for i, (hex1_idx, hex2_idx) in enumerate(solution_path):
            progress_msg = f"Executing... Step {i+1}/{len(solution_path)}: Clicking {hex1_idx} & {hex2_idx}"
            # Use log for the first message, then update_last_line for subsequent ones
            if i == 0:
                self._log(progress_msg)
            else:
                self._update_last_line(progress_msg)

            # Get coordinates from GridManager
            x1, y1 = self.gm.hex_centers[hex1_idx]
            x2, y2 = self.gm.hex_centers[hex2_idx]

            # Click the first hex
            self.wm.move_to(x1, y1, duration=move_duration)
            self.wm.click(x1, y1)
            time.sleep(click_delay)

            # Click the second hex
            self.wm.move_to(x2, y2, duration=move_duration)
            self.wm.click(x2, y2)
            time.sleep(click_delay)

        # --- Finalizing Click ---
        self._update_last_line("Execution complete. Finalizing...")
        time.sleep(0.5)
        center_x, center_y = self.gm.hex_centers[45]
        self.wm.click(center_x, center_y)

        self._update_last_line("Automation finished!")

    def _log(self, message):
        """Logs a new message to the overlay or console."""
        if self.overlay_manager:
            self.overlay_manager.log(message)
        else:
            print(message)

    def _update_last_line(self, message):
        """Updates the last line of the overlay or console."""
        if self.overlay_manager:
            self.overlay_manager.update_last_line(message)
        else:
            # Mimic the behavior for the console
            print(f"\r{message}", end="", flush=True)

