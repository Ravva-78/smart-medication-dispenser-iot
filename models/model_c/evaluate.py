import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import transforms, models
from pathlib import Path
import sys
import cv2
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report, roc_auc_score, roc_curve, precision_recall_curve
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from models.model_c.train import PocketDataset, CLASSES, DEVICE, IMG_SIZE

DATA_DIR = Path(__file__).parent / "dataset"
MODEL_PATH = Path(__file__).parent / "model_c.pt"
if not MODEL_PATH.exists():
    MODEL_PATH = Path(__file__).parent.parent / "production" / "ModelC_v1.0.pt"

EVAL_DIR = Path(__file__).parent / "runs" / "eval"

def load_model():
    model = models.mobilenet_v3_small()
    in_feat = int(getattr(model.classifier[3], "in_features", 1024))
    model.classifier[3] = nn.Linear(in_feat, 2)
    state = torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model

def generate_visual_batch_grid(dataset, model, output_path, n_samples=16):
    """Generate a 4x4 visual grid of prediction crops with colored overlays."""
    indices = np.random.choice(len(dataset), min(n_samples, len(dataset)), replace=False)
    
    fig, axes = plt.subplots(4, 4, figsize=(12, 12))
    axes = axes.flatten()
    
    tfm = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    for i, idx in enumerate(indices):
        img_path, true_label_idx = dataset.paths[idx], dataset.labels[idx]
        raw_img = cv2.imread(str(img_path))
        if raw_img is None:
            continue
        rgb_img = cv2.cvtColor(raw_img, cv2.COLOR_BGR2RGB)
        
        tensor_img = tfm(rgb_img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            outputs = model(tensor_img)
            probs = torch.softmax(outputs, 1)[0]
            pred_idx = int(torch.argmax(probs).item())
            conf = float(probs[pred_idx].item())

        true_cls = CLASSES[true_label_idx]
        pred_cls = CLASSES[pred_idx]
        
        color = 'green' if true_cls == pred_cls else 'red'
        
        axes[i].imshow(rgb_img)
        axes[i].set_title(f"True: {true_cls}\nPred: {pred_cls} ({conf:.2f})", color=color, fontsize=10, fontweight='bold')
        axes[i].axis('off')

    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"  -> Saved prediction grid plot: {output_path.name}")

def generate_roc_pr_curves(y_true, y_probs, output_path):
    """Generate ROC and Precision-Recall Curves."""
    fpr, tpr, _ = roc_curve(y_true, y_probs)
    precision, recall, _ = precision_recall_curve(y_true, y_probs)
    auc = roc_auc_score(y_true, y_probs)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # ROC Curve
    ax1.plot(fpr, tpr, color='blue', lw=2, label=f'ROC Curve (AUC = {auc:.4f})')
    ax1.plot([0, 1], [0, 1], color='gray', linestyle='--')
    ax1.set_xlabel('False Positive Rate')
    ax1.set_ylabel('True Positive Rate')
    ax1.set_title('Model C - ROC Curve')
    ax1.legend(loc='lower right')
    ax1.grid(True, alpha=0.3)
    
    # PR Curve
    ax2.plot(recall, precision, color='purple', lw=2, label='Precision-Recall Curve')
    ax2.set_xlabel('Recall')
    ax2.set_ylabel('Precision')
    ax2.set_title('Model C - Precision-Recall Curve')
    ax2.legend(loc='lower left')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()
    print(f"  -> Saved ROC/PR Curves: {output_path.name}")

def evaluate():
    if not MODEL_PATH.exists():
        print(f"No model found at {MODEL_PATH}. Train first.")
        return

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    model = load_model()
    
    tfm = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    for split in ["val", "test"]:
        split_ds = PocketDataset(DATA_DIR, split, tfm)
        if len(split_ds) == 0:
            continue

        loader = DataLoader(split_ds, batch_size=32, shuffle=False, num_workers=0)
        all_preds = []
        all_labels = []
        all_probs = []

        with torch.no_grad():
            for imgs, labels in loader:
                imgs = imgs.to(DEVICE)
                outputs = model(imgs)
                probs = torch.softmax(outputs, 1)
                _, preds = torch.max(outputs, 1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                all_probs.extend(probs[:, 1].cpu().numpy())

        acc = np.mean(np.array(all_preds) == np.array(all_labels))
        cm = confusion_matrix(all_labels, all_preds)
        cm_norm = confusion_matrix(all_labels, all_preds, normalize='true')
        auc = roc_auc_score(all_labels, all_probs) if len(set(all_labels)) > 1 else 0

        print(f"\n==========================================")
        print(f"=== Model C Evaluation [{split.upper()} SET] ===")
        print(f"==========================================")
        print(f"Accuracy:  {acc:.4f} ({acc*100:.2f}%)")
        print(f"AUC-ROC:   {auc:.4f}")
        print(f"Samples:   {len(all_labels)}")
        print(f"\nClassification Report ({split.upper()}):")
        print(classification_report(all_labels, all_preds, target_names=CLASSES, zero_division=0))

        # 1. Raw Confusion Matrix Heatmap
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt="d", xticklabels=CLASSES, yticklabels=CLASSES, cmap="Blues")
        plt.xlabel("Predicted Label")
        plt.ylabel("True Label")
        plt.title(f"Model C Confusion Matrix (Raw counts) [{split.upper()}]\nAccuracy: {acc*100:.2f}%")
        plt.tight_layout()
        cm_path = EVAL_DIR / f"confusion_matrix_{split}.png"
        plt.savefig(cm_path, dpi=200)
        plt.close()
        print(f"  -> Saved raw confusion matrix: {cm_path.name}")

        # 2. Normalized Confusion Matrix Heatmap
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm_norm, annot=True, fmt=".2%", xticklabels=CLASSES, yticklabels=CLASSES, cmap="Blues")
        plt.xlabel("Predicted Label")
        plt.ylabel("True Label")
        plt.title(f"Model C Confusion Matrix (Normalized) [{split.upper()}]\nAccuracy: {acc*100:.2f}%")
        plt.tight_layout()
        cm_norm_path = EVAL_DIR / f"confusion_matrix_normalized_{split}.png"
        plt.savefig(cm_norm_path, dpi=200)
        plt.close()
        print(f"  -> Saved normalized confusion matrix: {cm_norm_path.name}")

        # 3. ROC & PR Curves
        roc_pr_path = EVAL_DIR / f"roc_pr_curves_{split}.png"
        generate_roc_pr_curves(all_labels, all_probs, roc_pr_path)

        # 4. Visual Prediction Grid
        grid_path = EVAL_DIR / f"val_batch_predictions_{split}.jpg"
        generate_visual_batch_grid(split_ds, model, grid_path, n_samples=16)

if __name__ == "__main__":
    evaluate()
