import torch
import torch.nn as nn
from torchvision import transforms, models
from pathlib import Path
import cv2
import numpy as np

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMG_SIZE = 224
CLASSES = ["present", "missing"]
MODEL_PATH = Path(__file__).parent / "model_c.pt"
if not MODEL_PATH.exists():
    MODEL_PATH = Path(__file__).parent.parent / "production" / "ModelC_v1.0.pt"


_transform = None

def get_transform():
    global _transform
    if _transform is None:
        _transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    return _transform

_model = None

def load_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Train first.")
        model = models.mobilenet_v3_small()
        in_feat = int(getattr(model.classifier[3], "in_features", 1024))
        model.classifier[3] = nn.Linear(in_feat, 2)
        state = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
        model.load_state_dict(state)
        model.to(DEVICE)
        model.eval()
        _model = model
    return _model

def predict(crop_img):
    """Classify a single pocket crop (numpy array BGR). Returns (class, confidence)."""
    model = load_model()
    tfm = get_transform()
    rgb = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
    tensor = tfm(rgb).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        prob = torch.softmax(model(tensor), 1)[0]
        pred = int(torch.argmax(prob).item())
    return CLASSES[pred], float(prob[pred].item())

def predict_batch(crop_imgs):
    """Classify multiple pocket crops. Returns list of (class, confidence)."""
    if not crop_imgs:
        return []
    model = load_model()
    tfm = get_transform()
    tensors = []
    for crop in crop_imgs:
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        tensors.append(tfm(rgb))
    batch = torch.stack(tensors).to(DEVICE)
    with torch.no_grad():
        probs = torch.softmax(model(batch), 1)
        preds = torch.argmax(probs, 1)
    return [(CLASSES[int(p.item())], float(probs[i, int(p.item())].item()))
            for i, p in enumerate(preds)]

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python predict.py <image_path>")
        sys.exit(1)

    img_path = Path(sys.argv[1])
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"Failed to load {sys.argv[1]}")
        sys.exit(1)

    cls, conf = predict(img)
    print(f"\n=== Model C Prediction ===")
    print(f"Image: {img_path.name}")
    print(f"Status: {cls.upper()} (Confidence: {conf:.4f})")

    # Display pop-up window
    annotated = cv2.resize(img, (300, 300))
    color = (0, 255, 0) if cls == "present" else (0, 0, 255)
    cv2.putText(annotated, f"{cls.upper()}: {conf:.2f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    
    window_name = f"Model C - {cls.upper()} ({conf:.2f})"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.imshow(window_name, annotated)
    print("Press any key to close the window...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
