import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np
import json
from collections import defaultdict
import sys
import os

# --- Path Correction ---
# Add the project root to the Python path to allow imports from 'src'
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
# --- End Path Correction ---

from src.window_manager import WindowManager
from src.grid_manager import GridManager

class TemplateCreatorApp:
    ELEMENTS = {
        "EMPTY": "空 (EMPTY)",
        "FIRE": "火 (红色)",
        "WATER": "水 (蓝色向下)",
        "EARTH": "土 (绿色向下)",
        "AIR": "风 (浅蓝色向上)",
        "SALT": "盐 (Θ)",
        "VITAE": "生 (VITAE)",
        "MORS": "殁 (MORS)",
        "QUICKSILVER": "水银 (☿)",
        "LEAD": "铅 (♄)",
        "TIN": "锡 (♃)",
        "IRON": "铁 (♂)",
        "COPPER": "铜 (♀)",
        "SILVER": "银 (☽)",
        "GOLD": "金 (☉)"
    }

    def __init__(self, root):
        self.root = root
        self.root.title("模板创建工具")

        self.template_counts = defaultdict(int)
        self.saved_files_history = []
        self.current_hex_index = 0
        self.history = [] # To track previous hex indices for the back button
        self.current_screenshot = None
        self.current_grid = None
        self.current_colors = None

        # --- GUI Setup ---
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Left side: Image display
        self.image_label = ttk.Label(self.main_frame, text="点击“捕获画面”开始")
        self.image_label.grid(row=0, column=0, rowspan=5, padx=10, pady=10)

        # Right side: Controls
        ttk.Label(self.main_frame, text="元素类型:").grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # --- Radio Button Frame ---
        radio_frame = ttk.Frame(self.main_frame)
        radio_frame.grid(row=1, column=1, sticky=tk.W)
        self.element_var = tk.StringVar()
        
        row, col = 0, 0
        for key, display_text in self.ELEMENTS.items():
            rb = ttk.Radiobutton(radio_frame, text=display_text, variable=self.element_var, value=display_text)
            rb.grid(row=row, column=col, sticky=tk.W)
            col += 1
            if col > 1: # 2 columns of radio buttons
                col = 0
                row += 1
        self.element_var.set(self.ELEMENTS["EMPTY"])

        self.is_darkened_var = tk.BooleanVar()
        self.darkened_check = ttk.Checkbutton(self.main_frame, text="是否被遮挡 (变暗)?", variable=self.is_darkened_var)
        self.darkened_check.grid(row=2, column=1, sticky=tk.W, pady=10)

        self.confirm_button = ttk.Button(self.main_frame, text="确认并下一个", command=self.confirm_and_next, state=tk.DISABLED)
        self.confirm_button.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        self.skip_button = ttk.Button(self.main_frame, text="跳过此单元格", command=self.skip_hex, state=tk.DISABLED)
        self.skip_button.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)

        self.back_button = ttk.Button(self.main_frame, text="后退一步", command=self.go_back, state=tk.DISABLED)
        self.back_button.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5)

        # Bottom: Actions and Status
        self.status_var = tk.StringVar(value="状态: 空闲")
        ttk.Label(self.main_frame, textvariable=self.status_var).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=10)

        self.capture_button = ttk.Button(self.main_frame, text="捕获画面并开始 / 继续", command=self.start_new_capture)
        self.capture_button.grid(row=7, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.save_button = ttk.Button(self.main_frame, text="退出", command=self.root.destroy, state=tk.NORMAL)
        self.save_button.grid(row=7, column=1, sticky=(tk.W, tk.E), pady=5)

    def start_new_capture(self):
        try:
            self.status_var.set("状态: 正在捕获画面...")
            self.root.update()
            wm = WindowManager()
            wm.focus()
            self.current_screenshot = wm.capture()
            self.current_grid = GridManager()
            self.current_colors = self.current_grid.get_hex_colors(self.current_screenshot)
            self.current_hex_index = 0
            self.history = [] # Reset history for new capture
            
            self.confirm_button.config(state=tk.NORMAL)
            self.skip_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.NORMAL)
            self.back_button.config(state=tk.DISABLED) # Can't go back at the start
            
            self.display_current_hex()
        except Exception as e:
            messagebox.showerror("错误", f"捕获画面或初始化网格失败。\n\n{e}\n\n请确保游戏正在运行且配置文件正确。")
            self.status_var.set("状态: 错误")

    def display_current_hex(self):
        if self.current_hex_index >= len(self.current_grid.hex_centers):
            total_templates = sum(self.template_counts.values())
            self.status_var.set(f"状态: 本轮捕获完成！已创建 {total_templates} 个模板。可再次捕获或退出。")
            self.confirm_button.config(state=tk.DISABLED)
            self.skip_button.config(state=tk.DISABLED)
            self.image_label.config(image='', text="本轮捕获完成")
            return

        self.status_var.set(f"状态: 正在处理单元格 {self.current_hex_index + 1} / {len(self.current_grid.hex_centers)}")
        self.back_button.config(state=tk.NORMAL if self.history else tk.DISABLED)
        
        x, y = self.current_grid.hex_centers[self.current_hex_index]
        radius = self.current_grid.sampling_radius
        
        # Crop and display the image of the hex
        img_cropped = self.current_screenshot[y-radius:y+radius, x-radius:x+radius]
        if img_cropped.size == 0:
            self.skip_hex() # Skip if crop is empty
            return
            
        img_resized = cv2.resize(img_cropped, (200, 200), interpolation=cv2.INTER_NEAREST)
        img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
        
        pil_img = Image.fromarray(img_rgb)
        tk_img = ImageTk.PhotoImage(pil_img)
        
        self.image_label.config(image=tk_img)
        self.image_label.image = tk_img # Keep a reference

    def confirm_and_next(self):
        display_name = self.element_var.get()
        # Find the English key corresponding to the selected Chinese display name
        element_key = next((key for key, value in self.ELEMENTS.items() if value == display_name), None)

        if not element_key:
            messagebox.showerror("错误", "无效的元素选择。")
            return

        is_darkened = self.is_darkened_var.get()
        
        self.save_template(element_key, is_darkened)
        
        self.history.append({"action": "confirm", "hex_index": self.current_hex_index})
        self.current_hex_index += 1
        self.display_current_hex()

    def save_template(self, element_name, is_darkened):
        """Crops, adds alpha channel, and saves the hex image as a template."""
        state = "darkened" if is_darkened else "normal"
        
        # Create directory if it doesn't exist
        template_dir = "assets/templates"
        os.makedirs(template_dir, exist_ok=True)
        
        # Increment count for this element type to get a unique filename
        self.template_counts[f"{element_name}_{state}"] += 1
        count = self.template_counts[f"{element_name}_{state}"]
        filename = f"{element_name}_{state}_{count:02d}.png"
        filepath = os.path.join(template_dir, filename)

        # --- Image Processing ---
        x, y = self.current_grid.hex_centers[self.current_hex_index]
        radius = self.current_grid.sampling_radius
        
        # Crop the original screenshot
        img_bgr = self.current_screenshot[y-radius:y+radius, x-radius:x+radius]
        if img_bgr.size == 0: return

        # Create a 4-channel BGRA image
        img_bgra = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2BGRA)
        
        # Create a circular mask
        center = (radius, radius)
        mask = np.zeros((img_bgr.shape[0], img_bgr.shape[1]), dtype=np.uint8)
        cv2.circle(mask, center, radius, (255), -1)
        
        # Apply the mask to the alpha channel
        img_bgra[:, :, 3] = mask
        
        # Save the result
        cv2.imwrite(filepath, img_bgra)
        self.saved_files_history.append(filepath)
        self.status_var.set(f"已保存: {filename}")

    def skip_hex(self):
        self.history.append({"action": "skip", "hex_index": self.current_hex_index})
        self.current_hex_index += 1
        self.display_current_hex()

    def go_back(self):
        if not self.history:
            return
            
        last_action = self.history.pop()
        
        # If the last action was a confirmation, delete the last saved file
        if last_action["action"] == "confirm":
            if self.saved_files_history:
                last_file = self.saved_files_history.pop()
                try:
                    os.remove(last_file)
                    self.status_var.set(f"已删除: {os.path.basename(last_file)}")
                except OSError as e:
                    self.status_var.set(f"删除失败: {e}")

        self.current_hex_index = last_action["hex_index"]
        self.confirm_button.config(state=tk.NORMAL)
        self.skip_button.config(state=tk.NORMAL)
        self.display_current_hex()


if __name__ == "__main__":
    root = tk.Tk()
    app = TemplateCreatorApp(root)
    root.mainloop()