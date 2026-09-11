import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms, models
from pathlib import Path
import cv2
import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
import matplotlib.pyplot as plt
import seaborn as sns
import random

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMG_SIZE = 224
BATCH_SIZE = 32
EPOCHS = 100
LR = 0.001
PATIENCE = 15

DATA_DIR = Path(__file__).parent / "dataset"
CLASSES = ["present", "missing"]
NUM_CLASSES = len(CLASSES)


class PocketDataset(Dataset):
    def __init__(self, root, split="train", transform=None):
        self.paths = []
        self.labels = []
        self.transform = transform

        for label_idx, cls in enumerate(CLASSES):
            cls_dir = root / split / cls
            if not cls_dir.exists():
                continue
            for f in sorted(cls_dir.iterdir()):
                if f.suffix.lower() in ('.jpg', '.jpeg', '.png'):
                    self.paths.append(f)
                    self.labels.append(label_idx)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img = cv2.imread(str(self.paths[idx]))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        if self.transform:
            img = self.transform(img)
        else:
            img = torch.tensor(img, dtype=torch.float32).permute(2, 0, 1) / 255.0
        return img, self.labels[idx]


def get_transforms():
    train_tfm = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomAffine(degrees=10, translate=(0.1, 0.1), scale=(0.9, 1.1)),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    val_tfm = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return train_tfm, val_tfm


def create_model():
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, NUM_CLASSES)
    return model.to(DEVICE)


def train():
    train_tfm, val_tfm = get_transforms()
    train_ds = PocketDataset(DATA_DIR, "train", train_tfm)
    val_ds = PocketDataset(DATA_DIR, "val", val_tfm)

    print(f"Train: {len(train_ds)} | Val: {len(val_ds)}")
    if len(train_ds) == 0:
        print("No training data found. Extract pocket crops first.")
        return

    train_loader = DataLoader(train_ds, BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, BATCH_SIZE, shuffle=False, num_workers=0)

    model = create_model()
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=LR)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_acc = 0.0
    patience_counter = 0
    history = {"train_loss": [], "val_loss": [], "val_acc": []}

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        scheduler.step()

        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        all_preds = []
        all_labels = []
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
                outputs = model(imgs)
                loss = criterion(outputs, labels)
                val_loss += loss.item()
                _, preds = torch.max(outputs, 1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())

        val_acc = correct / total if total > 0 else 0
        train_loss_avg = train_loss / len(train_loader)
        val_loss_avg = val_loss / len(val_loader) if len(val_loader) > 0 else 0

        history["train_loss"].append(train_loss_avg)
        history["val_loss"].append(val_loss_avg)
        history["val_acc"].append(val_acc)

        print(f"Epoch {epoch:3d}/{EPOCHS} | Train Loss: {train_loss_avg:.4f} | Val Loss: {val_loss_avg:.4f} | Val Acc: {val_acc:.4f}", flush=True)

        if val_acc > best_acc:
            best_acc = val_acc
            patience_counter = 0
            torch.save(model.state_dict(), Path(__file__).parent / "model_c.pt")
            prod_model_path = Path(__file__).parent.parent / "models" / "production" / "ModelC_v1.0.pt"
            prod_model_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), prod_model_path)
            print(f"  -> Saved new best model (acc={val_acc:.4f}) to model_c.pt and models/production/ModelC_v1.0.pt", flush=True)


        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                print(f"Early stopping at epoch {epoch}")
                break

    print(f"\nTraining done. Best val accuracy: {best_acc:.4f}")

    if len(all_preds) > 0:
        cm = confusion_matrix(all_labels, all_preds)
        plt.figure(figsize=(6, 5))
        sns.heatmap(cm, annot=True, fmt="d", xticklabels=CLASSES, yticklabels=CLASSES)
        plt.xlabel("Predicted")
        plt.ylabel("True")
        plt.title("Confusion Matrix - Model C")
        plt.savefig(Path(__file__).parent / "confusion_matrix.png", dpi=150)
        plt.close()

        print("\nClassification Report:")
        print(classification_report(all_labels, all_preds, target_names=CLASSES, zero_division=0))


if __name__ == "__main__":
    train()
