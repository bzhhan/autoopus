import win32gui
import win32con
import mss
import numpy as np
import time
import win32api

class WindowManager:
    """
    Manages the game window, including finding it, capturing its content,
    and handling mouse/keyboard inputs.
    """

    def __init__(self, window_name="Opus Magnum"):
        """
        Initializes the WindowManager by finding the game window.

        Args:
            window_name (str): The title of the window to find.
        """
        self._hwnd = None
        self._window_name = window_name
        self._candidates = []
        win32gui.EnumWindows(self._enum_callback, None)

        if not self._candidates:
            raise Exception(f"Window containing '{window_name}' not found.")

        # Sort candidates by title length (shortest first) to find the best match
        self._candidates.sort(key=lambda item: len(item[1]))
        self._hwnd = self._candidates[0][0]
        
        self._sct = mss.mss()
        title = self.get_window_title()
        print(f"Window '{title}' found with handle: {self._hwnd}")

    def _enum_callback(self, hwnd, extra):
        """Callback for EnumWindows, collecting all potential candidates."""
        title = win32gui.GetWindowText(hwnd)
        if self._window_name in title:
            self._candidates.append((hwnd, title))

    def get_window_title(self):
        """Gets the title of the found window."""
        return win32gui.GetWindowText(self._hwnd)

    def focus(self):
        """Brings the window to the foreground before performing actions."""
        if win32gui.IsIconic(self._hwnd):
            win32gui.ShowWindow(self._hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(self._hwnd)
        time.sleep(0.2) # Wait a bit for the window to become active

    def get_window_rect(self):
        """
        Gets the bounding rectangle of the window.

        Returns:
            dict: A dictionary with 'left', 'top', 'width', and 'height'.
        """
        rect = win32gui.GetWindowRect(self._hwnd)
        x, y, x2, y2 = rect
        width = x2 - x
        height = y2 - y
        return {"left": x, "top": y, "width": width, "height": height}

    def capture(self):
        """
        Captures the content of the window.

        Returns:
            np.ndarray: The captured image as a NumPy array in BGR format.
        """
        monitor = self.get_window_rect()
        sct_img = self._sct.grab(monitor)
        img = np.array(sct_img)
        return img[:, :, :3]

    def window_to_screen(self, x, y):
        """Converts window-relative coordinates to screen-absolute coordinates."""
        rect = self.get_window_rect()
        screen_x = rect['left'] + x
        screen_y = rect['top'] + y
        return screen_x, screen_y

    def click(self, x, y, button='left'):
        """
        Moves to the given window-relative coordinates and clicks instantly.
        """
        self.focus()
        screen_x, screen_y = self.window_to_screen(x, y)
        
        # Move the cursor instantly
        win32api.SetCursorPos((screen_x, screen_y))
        
        # Perform the click
        if button == 'left':
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, screen_x, screen_y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, screen_x, screen_y, 0, 0)
        elif button == 'right':
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, screen_x, screen_y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, screen_x, screen_y, 0, 0)

    def move_to(self, x, y, duration=0):
        """
        Moves the mouse instantly to the given window-relative coordinates.
        The 'duration' parameter is kept for compatibility but is ignored.
        """
        self.focus()
        screen_x, screen_y = self.window_to_screen(x, y)
        win32api.SetCursorPos((screen_x, screen_y))

if __name__ == '__main__':
    try:
        wm = WindowManager()
        print("WindowManager initialized successfully.")
        rect = wm.get_window_rect()
        print(f"Window rect: {rect}")

        # Example of capturing the screen
        print("Attempting to capture the window...")
        screenshot = wm.capture()
        print(f"Capture successful. Image shape: {screenshot.shape}")

        # Example of mouse control
        print("Testing mouse control...")
        center_x = rect['width'] // 2
        center_y = rect['height'] // 2
        wm.move_to(center_x, center_y)
        print(f"Mouse moved to window-relative center: ({center_x}, {center_y})")
        wm.click()
        print("Mouse clicked at center.")

    except Exception as e:
        print(e)