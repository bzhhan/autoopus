import tkinter as tk
from collections import deque

class OverlayManager:
    """
    Manages a transparent, console-like overlay in the corner of a parent window.
    """

    def __init__(self, parent_rect, width=500, height=250, max_lines=10):
        """
        Initializes the overlay window.

        Args:
            parent_rect (dict): The geometry of the parent window.
            width (int): The width of the overlay.
            height (int): The height of the overlay.
            max_lines (int): The maximum number of log lines to display.
        """
        self.root = tk.Tk()
        self.width = width
        self.height = height
        self.line_height = 20
        self.padding = 5

        # Use a deque to automatically manage message history
        self.messages = deque(maxlen=max_lines)

        # --- Window Setup ---
        self.root.attributes("-transparentcolor", "black")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # Position the window at the bottom-left of the parent
        left = parent_rect['left'] + self.padding
        top = parent_rect['top'] + parent_rect['height'] - self.height - self.padding
        geo_str = f"{self.width}x{self.height}+{left}+{top}"
        self.root.geometry(geo_str)

        self.canvas = tk.Canvas(self.root, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.log("Overlay Initialized.")

    def log(self, message):
        """Adds a new message to the log and redraws the overlay."""
        self.messages.append(message)
        self._redraw()

    def update_last_line(self, message):
        """Replaces the last message in the log and redraws."""
        if self.messages:
            self.messages[-1] = message
        else:
            self.messages.append(message)
        self._redraw()

    def _redraw(self):
        """Clears and redraws all messages on the canvas."""
        self.canvas.delete("all")
        
        # Draw messages from the bottom up
        y_pos = self.height - self.padding
        for msg in reversed(self.messages):
            self.canvas.create_text(
                self.padding, y_pos,
                text=msg,
                fill="lime",
                font=("Consolas", 12),
                anchor="sw" # Anchor to the south-west (bottom-left)
            )
            y_pos -= self.line_height

        self.root.update()

    def update(self):
        """Updates the overlay window state."""
        self.root.update()

if __name__ == '__main__':
    import time
    try:
        dummy_geometry = {'left': 100, 'top': 100, 'width': 1280, 'height': 720}
        overlay = OverlayManager(dummy_geometry)

        for i in range(15):
            overlay.log(f"This is log message number {i+1}")
            time.sleep(0.5)
        
        print("Test complete.")

    except Exception as e:
        print(f"An error occurred: {e}")