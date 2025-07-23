import json
import cv2
import numpy as np
import math

class GridManager:
    """
    Manages a 'pointy-top' hexagonal game grid, defined by the left-most and
    right-most hexes on its horizontal centerline.
    """

    def __init__(self, config_path="config/grid_config.json"):
        """
        Initializes the GridManager by loading the config and calculating
        hexagonal cell center points.
        """
        with open(config_path, 'r') as f:
            config = json.load(f)

        self.grid_radius = config['grid_radius']
        self.sampling_radius_ratio = config['sampling_radius_ratio']
        
        p_left = config['anchor_points']['left_most_hex_center']
        p_right = config['anchor_points']['right_most_hex_center']
        
        # --- Calculate grid properties from anchors ---
        # The horizontal distance between the left-most and right-most hex centers
        # covers a span of 2 * grid_radius hex widths.
        self.hex_width = (p_right['x'] - p_left['x']) / (2 * self.grid_radius)
        self.hex_size = self.hex_width / math.sqrt(3)
        self.hex_height = 2 * self.hex_size
        
        # The center of the entire grid is the midpoint of the anchors.
        self.grid_center_x = (p_left['x'] + p_right['x']) / 2
        self.grid_center_y = p_left['y'] # y is constant on the horizontal centerline

        self.sampling_radius = int(self.hex_size * self.sampling_radius_ratio)
        
        self.axial_to_index = {}
        self.index_to_axial = []
        self.hex_centers = self._calculate_hex_centers()
        self.neighbors = self._calculate_neighbors()

    def _calculate_hex_centers(self):
        """
        Calculates the pixel coordinates for each cell in a 'pointy-top'
        hexagonal grid using axial coordinates. Also populates mapping between
        axial coordinates and list indices.
        """
        centers = []
        idx = 0
        for q in range(-self.grid_radius, self.grid_radius + 1):
            r1 = max(-self.grid_radius, -q - self.grid_radius)
            r2 = min(self.grid_radius, -q + self.grid_radius)
            for r in range(r1, r2 + 1):
                # Store mappings
                self.axial_to_index[(q, r)] = idx
                self.index_to_axial.append((q, r))
                
                # Convert axial coordinates (q, r) to pixel coordinates for pointy-top
                x = self.grid_center_x + self.hex_size * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
                y = self.grid_center_y + self.hex_size * (3./2. * r)
                centers.append((int(x), int(y)))
                idx += 1
        return centers

    def _calculate_neighbors(self):
        """
        Pre-calculates the 6 neighbors for each hex index on the grid.
        """
        # Axial directions for the 6 neighbors in a pointy-top grid
        axial_directions = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
        
        all_neighbors = []
        for i in range(len(self.index_to_axial)):
            q, r = self.index_to_axial[i]
            hex_neighbors = []
            for dq, dr in axial_directions:
                neighbor_q, neighbor_r = q + dq, r + dr
                neighbor_idx = self.axial_to_index.get((neighbor_q, neighbor_r), -1) # -1 if neighbor is off-grid
                hex_neighbors.append(neighbor_idx)
            all_neighbors.append(hex_neighbors)
        return all_neighbors

    def get_hex_colors(self, image):
        """
        Samples the average color from a circular region at the center of each hex.
        """
        colors = []
        for (x, y) in self.hex_centers:
            mask = np.zeros(image.shape[:2], dtype="uint8")
            cv2.circle(mask, (x, y), self.sampling_radius, 255, -1)
            mean_color = cv2.mean(image, mask=mask)[:3]
            colors.append(tuple(int(c) for c in mean_color))
        return colors

    def draw_grid_on_image(self, image):
        """
        Draws the calculated grid points and sampling circles on a given image.
        """
        img_copy = image.copy()
        for i, (x, y) in enumerate(self.hex_centers):
            cv2.circle(img_copy, (x, y), self.sampling_radius, (0, 255, 255), 1)
            cv2.circle(img_copy, (x, y), 2, (0, 0, 255), -1)
            cv2.putText(img_copy, str(i), (x + 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        return img_copy

if __name__ == '__main__':
    from window_manager import WindowManager
    
    print("Running GridManager test...")
    try:
        wm = WindowManager()
        wm.focus()
        screenshot = wm.capture()
        print("Screenshot captured.")

        grid = GridManager()
        print(f"GridManager initialized with {len(grid.hex_centers)} hexes.")

        img_with_grid = grid.draw_grid_on_image(screenshot)
        print("Grid drawn on image.")

        output_path = "capture_with_grid.png"
        cv2.imwrite(output_path, img_with_grid)
        print(f"Debug image saved to '{output_path}'")

        colors = grid.get_hex_colors(screenshot)
        print("\nSampled Hex Colors (BGR):")
        for i, color in enumerate(colors):
            print(f"  Hex {i:2d}: {color}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure the game is running and the coordinates in 'config/grid_config.json' are correct.")
    finally:
        input("\nPress Enter to exit...")