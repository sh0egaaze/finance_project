import os
import sys
import json
import torch
import torch.nn as nn
import math
import time
import numpy as np
from torch.utils.data import Dataset, DataLoader
from torch.cuda.amp import autocast, GradScaler
from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
from tqdm import tqdm

# Настройка путей
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
sys.path.insert(0, PROJECT_DIR)

# ============================================================
# КОНФИГУРАЦИЯ ОБУЧЕНИЯ (Из файла 1)
# ============================================================
class TrainConfig:
    pretrained_model_name = "DeepPavlov/rubert-base-cased"
    max_seq_length = 64
    batch_size = 32
    learning_rate = 2e-5
    num_epochs = 10
    warmup_ratio = 0.1
    weight_decay = 0.01
    num_bio_labels = 3
    fp16 = True
    device = "cuda" if torch.cuda.is_available() else "cpu"

# ============================================================
# АРХИТЕКТУРА МОДЕЛИ (Файл 4)
# ============================================================
class FinanceNLPModel(nn.Module):
    def __init__(self, pretrained_model_name: str, num_bio_labels: int = 3):
        super().__init__()
        self.bert = AutoModel.from_pretrained(pretrained_model_name)
        hidden_size = self.bert.config.hidden_size
        
        self.amount_head = nn.Sequential(
            nn.Dropout(0.1), nn.Linear(hidden_size, 256), nn.GELU(),
            nn.Dropout(0.1), nn.Linear(256, 64), nn.GELU(), nn.Linear(64, 1)
        )
        self.income_head = nn.Sequential(
            nn.Dropout(0.1), nn.Linear(hidden_size, 128), nn.GELU(),
            nn.Dropout(0.1), nn.Linear(128, 2)
        )
        self.description_head = nn.Sequential(
            nn.Dropout(0.1), nn.Linear(hidden_size, 128), nn.GELU(),
            nn.Dropout(0.1), nn.Linear(128, num_bio_labels)
        )
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls_output = outputs.last_hidden_state[:, 0, :]
        sequence_output = outputs.last_hidden_state
        return self.amount_head(cls_output), self.income_head(cls_output), self.description_head(sequence_output)

class MultiTaskLoss(nn.Module):
    def __init__(self, w_amt=1.0, w_inc=1.0, w_bio=1.0):
        super().__init__()
        self.weights = [w_amt, w_inc, w_bio]
        self.mse = nn.MSELoss()
        self.ce_inc = nn.CrossEntropyLoss()
        self.ce_bio = nn.CrossEntropyLoss(ignore_index=-100)

    def forward(self, p_amt, p_inc, p_bio, t_amt, t_inc, t_bio, mask):
        l_amt = self.mse(p_amt.squeeze(-1), t_amt)
        l_inc = self.ce_inc(p_inc, t_inc)
        t_bio_masked = t_bio.clone()
        t_bio_masked[mask == 0] = -100
        l_bio = self.ce_bio(p_bio.view(-1, 3), t_bio_masked.view(-1))
        total = self.weights[0]*l_amt + self.weights[1]*l_inc + self.weights[2]*l_bio
        return total, {"loss_total": total.item(), "loss_amount": l_amt.item(), "loss_income": l_inc.item(), "loss_bio": l_bio.item()}

# ============================================================
# DATASET (Файл 3)
# ============================================================
class FinanceDataset(Dataset):
    def __init__(self, data_path, tokenizer, max_length=64):
        with open(data_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self): return len(self.data)

    def _create_bio_labels(self, text, description, encoding):
        labels = [0] * len(encoding.input_ids)
        t_low, d_low = text.lower(), description.lower()
        start = t_low.find(d_low)
        if start == -1 and len(d_low) >= 3:
            start = t_low.find(d_low[:3])
        if start != -1:
            end = start + len(d_low)
            first = True
            for i in range(len(encoding.input_ids)):
                span = encoding.token_to_chars(i)
                if span and span[0] < end and span[1] > start:
                    labels[i] = 1 if first else 2
                    first = False
        return labels

    def __getitem__(self, idx):
        s = self.data[idx]
        enc = self.tokenizer(s["text"], max_length=self.max_length, padding="max_length", truncation=True, return_tensors="pt")
        bio = self._create_bio_labels(s["text"], s["description"], enc)
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "amount": torch.tensor(math.log(max(s["amount"], 1.0)), dtype=torch.float32),
            "is_income": torch.tensor(int(s["is_income"]), dtype=torch.long),
            "bio_labels": torch.tensor(bio, dtype=torch.long),
            "original_amount": torch.tensor(s["amount"], dtype=torch.float32)
        }

# ============================================================
# МЕТРИКИ И ОБУЧЕНИЕ (Файл 5)
# ============================================================
def compute_metrics(model, loader, device):
    model.eval()
    errors, inc_c, inc_t, bio_c, bio_t = [], 0, 0, 0, 0
    with torch.no_grad():
        for b in loader:
            ids, mask = b["input_ids"].to(device), b["attention_mask"].to(device)
            p_amt, p_inc, p_bio = model(ids, mask)
            
            # Amount MAPE
            preds_amt = np.exp(p_amt.squeeze(-1).cpu().numpy())
            trues_amt = b["original_amount"].numpy()
            errors.extend([abs(p - t) / max(t, 1) * 100 for p, t in zip(preds_amt, trues_amt)])
            
            # Income Acc
            inc_c += (p_inc.argmax(-1).cpu().numpy() == b["is_income"].numpy()).sum()
            inc_t += len(b["is_income"])
            
            # BIO Acc
            preds_bio = p_bio.argmax(-1).cpu()
            for i in range(len(preds_bio)):
                m = mask[i].cpu().bool()
                bio_c += (preds_bio[i][m] == b["bio_labels"][i][m]).sum().item()
                bio_t += m.sum().item()
    return {"amount_mape": np.mean(errors), "income_accuracy": inc_c/inc_t*100, "bio_accuracy": bio_c/bio_t*100}

def train():
    c = TrainConfig()
    print(f"🚀 Обучение на {c.device}...")
    tokenizer = AutoTokenizer.from_pretrained(c.pretrained_model_name)
    train_ds = FinanceDataset(os.path.join(BASE_DIR, "data", "dataset_train.json"), tokenizer)
    val_ds = FinanceDataset(os.path.join(BASE_DIR, "data", "dataset_val.json"), tokenizer)
    
    train_loader = DataLoader(train_ds, batch_size=c.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=c.batch_size)
    
    model = FinanceNLPModel(c.pretrained_model_name).to(c.device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=c.learning_rate)
    
    total_steps = len(train_loader) * c.num_epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, int(total_steps*c.warmup_ratio), total_steps)
    criterion = MultiTaskLoss()
    scaler = GradScaler(enabled=c.fp16)

    best_loss = float("inf")
    for epoch in range(c.num_epochs):
        model.train()
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}")
        for b in pbar:
            ids, mask = b["input_ids"].to(c.device), b["attention_mask"].to(c.device)
            with autocast(enabled=c.fp16):
                p_amt, p_inc, p_bio = model(ids, mask)
                loss, ld = criterion(p_amt, p_inc, p_bio, b["amount"].to(c.device), b["is_income"].to(c.device), b["bio_labels"].to(c.device), mask)
            
            optimizer.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            pbar.set_postfix(loss=f"{loss.item():.4f}")
        
        metrics = compute_metrics(model, val_loader, c.device)
        print(f"📊 Epoch {epoch+1}: MAPE: {metrics['amount_mape']:.1f}%, Inc Acc: {metrics['income_accuracy']:.1f}%, BIO Acc: {metrics['bio_accuracy']:.1f}%")
        
        if loss.item() < best_loss:
            best_loss = loss.item()
            save_path = os.path.join(PROJECT_DIR, "backend", "app", "ml", "trained_models", "nlp_parser")
            os.makedirs(save_path, exist_ok=True)
            torch.save({"model_state_dict": model.state_dict(), "config": {"pretrained_model_name": c.pretrained_model_name, "num_bio_labels": 3, "max_seq_length": 64}}, os.path.join(save_path, "checkpoint.pt"))
            tokenizer.save_pretrained(os.path.join(save_path, "tokenizer"))

if __name__ == "__main__":
    train()
