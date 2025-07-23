import os
import cv2
import numpy as np
from collections import Counter

from src.window_manager import WindowManager
from src.grid_manager import GridManager

class ElementDetector:
    """
    Detects game elements by matching cropped hex images against a library
    of pre-made templates.
    """

    def __init__(self, template_dir="assets/templates", match_threshold=0.6):
        """
        Initializes the detector by loading all templates from the specified
        directory.
        """
        self.templates = []
        self.match_threshold = match_threshold
        
        print(f"Loading templates from '{template_dir}'...")
        if not os.path.isdir(template_dir):
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        for filename in os.listdir(template_dir):
            if filename.endswith(".png"):
                try:
                    path = os.path.join(template_dir, filename)
                    template_image = cv2.imread(path, cv2.IMREAD_UNCHANGED)
                    
                    parts = os.path.splitext(filename)[0].split('_')
                    element = parts[0]
                    state = parts[1]
                    
                    self.templates.append({
                        "element": element,
                        "state": state,
                        "image": template_image
                    })
                except Exception as e:
                    print(f"Warning: Could not load or parse template {filename}. Error: {e}")
        
        if not self.templates:
            raise ValueError("No templates were loaded. Please run create_templates.py first.")
        print(f"Successfully loaded {len(self.templates)} templates.")

    def identify_elements(self, screenshot, grid):
        """
        Identifies the element in each hex cell by finding the best template match.
        """
        identified_elements = []
        
        for x, y in grid.hex_centers:
            radius = grid.sampling_radius
            
            hex_roi = screenshot[y-radius:y+radius, x-radius:x+radius]
            if hex_roi.size == 0:
                identified_elements.append({"element": "OUT_OF_BOUNDS", "state": "normal"})
                continue

            best_match_score = -1
            best_match_info = {"element": "UNKNOWN", "state": "normal"}

            for template_info in self.templates:
                template_img_orig = template_info["image"]
                
                # --- Dynamic Template Resizing ---
                # Resize template to match the current ROI size for scale invariance.
                # This makes detection robust to changes in game resolution or UI scaling.
                h, w = hex_roi.shape[:2]
                resized_template = cv2.resize(template_img_orig, (w, h), interpolation=cv2.INTER_AREA)

                mask = resized_template[:,:,3]
                result = cv2.matchTemplate(hex_roi, resized_template[:,:,:3], cv2.TM_CCOEFF_NORMED, mask=mask)
                _, max_val, _, _ = cv2.minMaxLoc(result)

                if max_val > best_match_score:
                    best_match_score = max_val
                    best_match_info = {
                        "element": template_info["element"],
                        "state": template_info["state"]
                    }
            
            if best_match_score < self.match_threshold:
                best_match_info = {"element": "UNKNOWN", "state": "normal"}

            identified_elements.append(best_match_info)
            
        return identified_elements

def draw_elements_on_image(image, grid, elements):
    """
    Draws the identified element names and a summary count onto the grid image.
    """
    img_copy = image.copy()
    
    # --- Draw element names on each hex ---
    for i, element_info in enumerate(elements):
        x, y = grid.hex_centers[i]
        
        element_name = element_info["element"]
        element_state = element_info["state"]
        
        text = element_name
        if element_state == "darkened":
            text += " (D)"
        
        color = (0, 255, 0)
        if element_name in ["UNKNOWN", "OUT_OF_BOUNDS"]:
            color = (0, 0, 255)

        if element_name != "OUT_OF_BOUNDS":
            cv2.putText(img_copy, text, (x + 10, y + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)

    # --- Count elements and draw the summary in a specific order ---
    element_counts = Counter(e['element'] for e in elements if e['element'] not in ["EMPTY", "OUT_OF_BOUNDS", "UNKNOWN"])
    
    display_order = [
        "FIRE", "WATER", "EARTH", "AIR", "SALT", "QUICKSILVER",
        "VITAE", "MORS", "LEAD", "TIN", "IRON", "COPPER", "SILVER", "GOLD"
    ]
    
    y_offset = 20
    cv2.putText(img_copy, "Element Counts:", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    y_offset += 25
    
    for element_name in display_order:
        count = element_counts.get(element_name, 0)
        if count > 0:
            cv2.putText(img_copy, f"{element_name}: {count}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_offset += 20

    return img_copy


if __name__ == '__main__':
    print("Running ElementDetector (Template Matching) test...")
    try:
        wm = WindowManager()
        grid = GridManager()
        detector = ElementDetector(match_threshold=0.6)
        print("Managers initialized.")

        wm.focus()
        screenshot = wm.capture()
        print("Screenshot captured.")

        identified_elements = detector.identify_elements(screenshot, grid)
        print("Element identification complete.")

        img_with_grid = grid.draw_grid_on_image(screenshot)
        img_with_elements = draw_elements_on_image(img_with_grid, grid, identified_elements)
        print("Drew element names on the image.")

        output_path = "capture_with_elements.png"
        cv2.imwrite(output_path, img_with_elements)
        print(f"Debug image with identified elements saved to '{output_path}'")

        print("\n--- Detection Summary ---")
        for i, element in enumerate(identified_elements):
            if element["element"] != "OUT_OF_BOUNDS":
                print(f"  Hex {i:2d}: {element['element']} ({element['state']})")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
