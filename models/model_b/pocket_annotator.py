import cv2
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_DIR = PROJECT_ROOT / "Model_B" / "modelB_dataset"
LABELS_DIR = PROJECT_ROOT / "Model_B" / "labels"
LABELS_DIR.mkdir(parents=True, exist_ok=True)


class PocketAnnotator:
    def __init__(self):
        self.images = sorted([f for f in DATASET_DIR.iterdir() 
                             if f.suffix.lower() in ('.jpg', '.jpeg', '.png')])
        self.idx = 0
        self.boxes = []
        self.selected = -1
        self.dragging = False
        self.drag_start = None
        self.drag_mode = None
        self.img = None
        self.img_display = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.max_w = 1400
        self.max_h = 900
        
    def load_image(self):
        if self.idx >= len(self.images):
            print("All images processed!")
            return False
            
        img_path = self.images[self.idx]
        self.img = cv2.imread(str(img_path))
        if self.img is None:
            print(f"Failed to load {img_path}")
            self.idx += 1
            return self.load_image()
            
        label_path = LABELS_DIR / f"{img_path.stem}.txt"
        self.boxes = []
        if label_path.exists():
            with open(label_path) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 5:
                        _, xc, yc, w, h = map(float, parts)
                        img_h, img_w = self.img.shape[:2]
                        x = int((xc - w/2) * img_w)
                        y = int((yc - h/2) * img_h)
                        w = int(w * img_w)
                        h = int(h * img_h)
                        self.boxes.append([x, y, w, h])
        
        if not self.boxes:
            self.boxes = self.auto_detect_pockets()
            
        self.selected = -1
        self.fit_to_window()
        return True
    
    def auto_detect_pockets(self):
        gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY_INV, 11, 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        img_h, img_w = self.img.shape[:2]
        min_area = (img_w * img_h) * 0.001
        max_area = (img_w * img_h) * 0.15
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue
            if len(cnt) >= 5:
                ellipse = cv2.fitEllipse(cnt)
                (cx, cy), (w, h), angle = ellipse
                aspect = max(w, h) / min(w, h) if min(w, h) > 0 else 0
                if aspect > 3.0:
                    continue
                x = int(cx - w/2)
                y = int(cy - h/2)
                w, h = int(w), int(h)
                x = max(0, x)
                y = max(0, y)
                w = min(w, img_w - x)
                h = min(h, img_h - y)
                if w > 10 and h > 10:
                    boxes.append([x, y, w, h])
        
        boxes = self.nms_boxes(boxes, 0.3)
        print(f"Auto-detected {len(boxes)} pockets in {self.images[self.idx].name}")
        return boxes
    
    def nms_boxes(self, boxes, iou_thresh):
        if not boxes:
            return []
        boxes = np.array(boxes, dtype=float)
        x1 = boxes[:, 0]
        y1 = boxes[:, 1]
        x2 = boxes[:, 0] + boxes[:, 2]
        y2 = boxes[:, 1] + boxes[:, 3]
        areas = boxes[:, 2] * boxes[:, 3]
        order = areas.argsort()[::-1]
        
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            inds = np.where(iou <= iou_thresh)[0]
            order = order[inds + 1]
        
        return boxes[keep].astype(int).tolist()
    
    def fit_to_window(self):
        h, w = self.img.shape[:2]
        self.scale = min(self.max_w / w, self.max_h / h, 1.0)
        new_w, new_h = int(w * self.scale), int(h * self.scale)
        self.img_display = cv2.resize(self.img, (new_w, new_h))
        self.offset_x = (self.max_w - new_w) // 2
        self.offset_y = (self.max_h - new_h) // 2
    
    def img_to_canvas(self, x, y):
        """Convert image coordinates to canvas coordinates"""
        return (int(x * self.scale) + self.offset_x, int(y * self.scale) + self.offset_y)
    
    def canvas_to_img(self, cx, cy):
        """Convert canvas coordinates to image coordinates"""
        return ((cx - self.offset_x) / self.scale, (cy - self.offset_y) / self.scale)
    
    def draw_boxes(self):
        canvas = np.zeros((self.max_h, self.max_w, 3), dtype=np.uint8)
        # Place image on canvas
        canvas[self.offset_y:self.offset_y+self.img_display.shape[0],
               self.offset_x:self.offset_x+self.img_display.shape[1]] = self.img_display
        
        for i, (x, y, w, h) in enumerate(self.boxes):
            x1, y1 = self.img_to_canvas(x, y)
            x2, y2 = self.img_to_canvas(x + w, y + h)
            
            color = (0, 255, 0) if i != self.selected else (0, 255, 255)
            thickness = 2 if i != self.selected else 3
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)
            
            if i == self.selected:
                handle_size = 8
                handles = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
                for hx, hy in handles:
                    cv2.rectangle(canvas, (hx - handle_size//2, hy - handle_size//2),
                                (hx + handle_size//2, hy + handle_size//2), (255, 0, 0), -1)
            
            cv2.putText(canvas, str(i+1), (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        info = f"Image {self.idx+1}/{len(self.images)}: {self.images[self.idx].name}"
        cv2.putText(canvas, info, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        help_text = "S=Save N=Next P=Prev A=Add Box Del=Delete Drag=Move Handle=Resize Q=Quit"
        cv2.putText(canvas, help_text, (20, self.max_h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        cv2.imshow("Pocket Annotation Assistant", canvas)
    
    def get_handle_at(self, mx, my):
        if self.selected < 0 or self.selected >= len(self.boxes):
            return None
        x, y, w, h = self.boxes[self.selected]
        x1, y1 = self.img_to_canvas(x, y)
        x2, y2 = self.img_to_canvas(x + w, y + h)
        
        handles = {'tl': (x1, y1), 'tr': (x2, y1), 'bl': (x1, y2), 'br': (x2, y2)}
        handle_size = 12
        for name, (hx, hy) in handles.items():
            if abs(mx - hx) <= handle_size and abs(my - hy) <= handle_size:
                return name
        return None
    
    def point_in_box(self, mx, my, box_idx):
        x, y, w, h = self.boxes[box_idx]
        x1, y1 = self.img_to_canvas(x, y)
        x2, y2 = self.img_to_canvas(x + w, y + h)
        return x1 <= mx <= x2 and y1 <= my <= y2
    
    def mouse_callback(self, event, mx, my, flags, param):
        # Convert mouse coords to image coords
        ix, iy = self.canvas_to_img(mx, my)
        ix, iy = int(ix), int(iy)
        
        if event == cv2.EVENT_LBUTTONDOWN:
            # Check resize handles first (in canvas coords)
            handle = self.get_handle_at(mx, my)
            if handle:
                self.dragging = True
                self.drag_mode = f'resize_{handle}'
                self.drag_start = (mx, my)
                return
            
            # Check if clicking inside a box
            for i in range(len(self.boxes)):
                if self.point_in_box(mx, my, i):
                    self.selected = i
                    self.dragging = True
                    self.drag_mode = 'move'
                    self.drag_start = (mx, my)
                    return
            
            # Click on empty space - start new box
            self.dragging = True
            self.drag_mode = 'new'
            self.drag_start = (mx, my)
            self.boxes.append([ix, iy, 0, 0])
            self.selected = len(self.boxes) - 1
            
        elif event == cv2.EVENT_MOUSEMOVE and self.dragging:
            cur_ix, cur_iy = self.canvas_to_img(mx, my)
            cur_ix, cur_iy = int(cur_ix), int(cur_iy)
            start_ix, start_iy = self.canvas_to_img(*self.drag_start)
            start_ix, start_iy = int(start_ix), int(start_iy)
            
            dx = cur_ix - start_ix
            dy = cur_iy - start_iy
            
            if self.drag_mode == 'move':
                x, y, w, h = self.boxes[self.selected]
                self.boxes[self.selected][0] = max(0, x + dx)
                self.boxes[self.selected][1] = max(0, y + dy)
                self.drag_start = (mx, my)
                
            elif self.drag_mode.startswith('resize_'):
                handle = self.drag_mode.split('_')[1]
                x, y, w, h = self.boxes[self.selected]
                if 't' in handle:
                    new_y = max(0, y + dy)
                    new_h = max(10, h - dy)
                    self.boxes[self.selected][1] = new_y
                    self.boxes[self.selected][3] = new_h
                if 'b' in handle:
                    new_h = max(10, h + dy)
                    self.boxes[self.selected][3] = new_h
                if 'l' in handle:
                    new_x = max(0, x + dx)
                    new_w = max(10, w - dx)
                    self.boxes[self.selected][0] = new_x
                    self.boxes[self.selected][2] = new_w
                if 'r' in handle:
                    new_w = max(10, w + dx)
                    self.boxes[self.selected][2] = new_w
                self.drag_start = (mx, my)
                
            elif self.drag_mode == 'new':
                x = max(0, min(start_ix, cur_ix))
                y = max(0, min(start_iy, cur_iy))
                w = max(10, abs(cur_ix - start_ix))
                h = max(10, abs(cur_iy - start_iy))
                self.boxes[self.selected] = [x, y, w, h]
                
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging = False
            self.drag_mode = None
            self.boxes = [b for b in self.boxes if b[2] > 10 and b[3] > 10]
            if self.selected >= len(self.boxes):
                self.selected = -1
    
    def save_labels(self):
        img_path = self.images[self.idx]
        label_path = LABELS_DIR / f"{img_path.stem}.txt"
        img_h, img_w = self.img.shape[:2]
        
        with open(label_path, 'w') as f:
            for x, y, w, h in self.boxes:
                xc = (x + w/2) / img_w
                yc = (y + h/2) / img_h
                nw = w / img_w
                nh = h / img_h
                f.write(f"0 {xc:.6f} {yc:.6f} {nw:.6f} {nh:.6f}\n")
        print(f"Saved {len(self.boxes)} boxes to {label_path.name}")
    
    def run(self):
        cv2.namedWindow("Pocket Annotation Assistant", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Pocket Annotation Assistant", self.max_w, self.max_h)
        cv2.setMouseCallback("Pocket Annotation Assistant", self.mouse_callback)
        
        if not self.load_image():
            return
            
        while True:
            self.draw_boxes()
            key = cv2.waitKey(30) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('s'):
                self.save_labels()
            elif key == ord('n'):
                self.save_labels()
                self.idx += 1
                if not self.load_image():
                    break
            elif key == ord('p'):
                self.save_labels()
                self.idx = max(0, self.idx - 1)
                self.load_image()
            elif key == ord('a'):
                img_h, img_w = self.img.shape[:2]
                cx, cy = img_w // 2, img_h // 2
                self.boxes.append([cx - 50, cy - 50, 100, 100])
                self.selected = len(self.boxes) - 1
            elif key == ord('d') or key == 8:
                if self.selected >= 0 and self.selected < len(self.boxes):
                    self.boxes.pop(self.selected)
                    self.selected = -1
            elif key == ord('r'):
                self.boxes = self.auto_detect_pockets()
                self.selected = -1
        
        cv2.destroyAllWindows()


if __name__ == "__main__":
    annotator = PocketAnnotator()
    annotator.run()