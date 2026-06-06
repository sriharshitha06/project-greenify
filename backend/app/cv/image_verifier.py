import os
import cv2
import numpy as np
import requests

class ActivityVerifier:
    def __init__(self):
        self.weights_dir = os.path.join(os.path.dirname(__file__), "weights")
        os.makedirs(self.weights_dir, exist_ok=True)
        
        self.prototxt_path = os.path.join(self.weights_dir, "MobileNetSSD_deploy.prototxt")
        self.model_path = os.path.join(self.weights_dir, "MobileNetSSD_deploy.caffemodel")
        
        self.net = None
        self.classes = [
            "background", "aeroplane", "bicycle", "bird", "boat",
            "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
            "dog", "horse", "motorbike", "person", "pottedplant",
            "sheep", "sofa", "train", "tvmonitor"
        ]
        
        # Download weights on background thread or lazy load
        self.download_model_files()
        self.load_network()

    def download_model_files(self):
        # Public URLs for MobileNet-SSD
        proto_url = "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/deploy.prototxt"
        model_url = "https://alexeyab84.github.io/yolo2_lightweight_jesson/weights/MobileNetSSD_deploy.caffemodel"
        
        try:
            if not os.path.exists(self.prototxt_path):
                print("Downloading MobileNet-SSD prototxt...")
                r = requests.get(proto_url, timeout=10)
                with open(self.prototxt_path, "wb") as f:
                    f.write(r.content)
            
            if not os.path.exists(self.model_path):
                print("Downloading MobileNet-SSD weights (~15MB)...")
                r = requests.get(model_url, timeout=20)
                with open(self.model_path, "wb") as f:
                    f.write(r.content)
        except Exception as e:
            print(f"Failed to download MobileNet-SSD weights: {e}. Falling back to classical CV.")

    def load_network(self):
        if os.path.exists(self.prototxt_path) and os.path.exists(self.model_path):
            try:
                self.net = cv2.dnn.readNetFromCaffe(self.prototxt_path, self.model_path)
                print("MobileNet-SSD loaded successfully in OpenCV.")
            except Exception as e:
                print(f"Error loading Caffe model: {e}. Reverting to classical CV.")

    def verify_image(self, img_path: str, activity_type: str) -> tuple[bool, float, str]:
        """
        Verifies if the image at img_path displays the requested activity.
        Returns: (is_verified, confidence, message)
        """
        if not os.path.exists(img_path):
            return False, 0.0, "File not found"

        # Load image
        img = cv2.imread(img_path)
        if img is None:
            return False, 0.0, "Invalid image format"

        # If Caffe model is loaded, use DNN object detection
        if self.net is not None:
            return self.verify_with_dnn(img, activity_type, img_path)
        else:
            return self.verify_with_classical_cv(img, activity_type)

    def verify_with_dnn(self, img, activity_type: str, img_path: str) -> tuple[bool, float, str]:
        h, w = img.shape[:2]
        # Preprocess image for MobileNet-SSD (resize to 300x300, scale, mean subtract)
        blob = cv2.dnn.blobFromImage(cv2.resize(img, (300, 300)), 0.007843, (300, 300), 127.5)
        self.net.setInput(blob)
        detections = self.net.forward()
        
        # Mapping activities to DNN classes
        # cycling -> bicycle
        # reusable_product -> bottle
        # public_transport -> bus, train
        # tree_planting -> pottedplant
        activity_targets = {
            "cycling": ["bicycle"],
            "reusable_product": ["bottle"],
            "public_transport": ["bus", "train"],
            "tree_planting": ["pottedplant"]
        }
        
        targets = activity_targets.get(activity_type.lower(), [])
        if not targets:
            return False, 0.0, f"Unsupported activity type: {activity_type}"

        max_conf = 0.0
        verified = False
        detected_objects = []

        # Loop over detections
        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            if confidence > 0.3:  # Threshold
                class_id = int(detections[0, 0, i, 1])
                class_name = self.classes[class_id]
                detected_objects.append(class_name)
                
                if class_name in targets:
                    verified = True
                    if confidence > max_conf:
                        max_conf = confidence
                        
                    # Draw bounding boxes and label on the image itself
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")
                    cv2.rectangle(img, (startX, startY), (endX, endY), (16, 185, 129), 3) # Greenify neon green (emerald)
                    label = f"{class_name}: {confidence:.2%}"
                    cv2.putText(img, label, (startX, startY - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (16, 185, 129), 2)
        
        # Save verified image with annotations back to path
        if verified:
            cv2.imwrite(img_path, img)
            return True, max_conf, f"Successfully verified: detected {', '.join(targets)} with confidence {max_conf:.1%}"
        
        # Fallback to classical CV if DNN is loaded but failed to detect
        # sometimes objects like reusable shopping bags aren't in MobileNet categories, or trees aren't in pots
        print(f"DNN did not detect targets {targets} (detected: {detected_objects}). Trying classical CV fallback.")
        return self.verify_with_classical_cv(img, activity_type)

    def verify_with_classical_cv(self, img, activity_type: str) -> tuple[bool, float, str]:
        """
        Fallbacks using classical image processing when DNN is absent or fails.
        """
        activity_type = activity_type.lower()
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        if activity_type == "tree_planting":
            # Segment GREEN color to detect plant foliage
            # Green hue range in HSV is roughly 35-85
            lower_green = np.array([35, 40, 40])
            upper_green = np.array([85, 255, 255])
            
            mask = cv2.inRange(hsv, lower_green, upper_green)
            green_pixels = cv2.countNonZero(mask)
            total_pixels = img.shape[0] * img.shape[1]
            green_ratio = green_pixels / total_pixels
            
            # If green ratio is substantial (e.g. > 15% of the image), we verify tree/plant activity
            if green_ratio > 0.15:
                conf = float(min(0.5 + green_ratio, 0.95))
                return True, conf, f"Verified tree planting via color segmentation (green ratio: {green_ratio:.1%})"
            else:
                return False, float(green_ratio), f"Failed verification: Insufficient green foliage detected (green ratio: {green_ratio:.1%})"
                
        elif activity_type == "cycling":
            # Detect wheels using Hough Circles or shape features
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (9, 9), 2)
            circles = cv2.HoughCircles(
                blurred, cv2.HOUGH_GRADIENT, dp=1, minDist=50,
                param1=100, param2=40, minRadius=20, maxRadius=150
            )
            
            if circles is not None:
                circle_count = len(circles[0])
                conf = float(min(0.5 + circle_count * 0.15, 0.9))
                return True, conf, f"Verified cycling: detected circular wheel shapes (circles detected: {circle_count})"
            else:
                # Check for high density of edges representing spokes/gears
                edges = cv2.Canny(gray, 50, 150)
                edge_density = cv2.countNonZero(edges) / (img.shape[0] * img.shape[1])
                if edge_density > 0.08:
                    return True, 0.55, "Verified cycling: high edge density of mechanical contours"
                return False, 0.2, "Failed verification: Could not detect wheel circles or metallic frame contours"
                
        elif activity_type == "reusable_product":
            # Check for high contrast item shape with vertical contours (cups, bottles)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            bottle_like_shapes = 0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 1000:
                    x, y, w, h_rect = cv2.boundingRect(cnt)
                    aspect_ratio = h_rect / w
                    # Bottles/cups are usually taller than wide (aspect ratio 1.2 to 4)
                    if 1.2 <= aspect_ratio <= 4.0:
                        bottle_like_shapes += 1
                        
            if bottle_like_shapes > 0:
                return True, 0.65, f"Verified reusable product: detected vertical cylindrical profile (cylinders found: {bottle_like_shapes})"
            return False, 0.3, "Failed verification: No bottle/cup profile detected"
            
        elif activity_type == "public_transport":
            # Buses/trains are large rectangular structures
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 30, 100)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            rectangular_shapes = 0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 5000:
                    x, y, w, h_rect = cv2.boundingRect(cnt)
                    aspect_ratio = w / h_rect # vehicles are usually wide
                    if aspect_ratio > 1.3:
                        rectangular_shapes += 1
                        
            if rectangular_shapes > 0:
                return True, 0.60, "Verified public transport: detected horizontal rectangular vehicle body"
            return False, 0.25, "Failed verification: Could not detect bus/train layout contours"
            
        else:
            # General fallback verification
            return True, 0.5, "Verified: Custom environment action submitted"

# Instantiate a single global verifier
verifier = ActivityVerifier()
