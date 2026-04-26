import os
import sys
import json
import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
from tqdm import tqdm

# Настройка путей
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
sys.path.insert(0, PROJECT_DIR)

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

class FinanceNLPModel(nn.Module):
    def __init__(self, pretrained_model_name: str, num_bio_labels: int = 3):
        super().__init__()
        self.bert = AutoModel.from_pretrained(pretrained_model_name)
        hidden_size = self.bert.config.hidden_size
        self.income_head = nn.Sequential(nn.Linear(hidden_size, 128), nn.GELU(), nn.Linear(128, 2))
        self.description_head = nn.Sequential(nn.Linear(hidden_size, 128), nn.GELU(), nn.Linear(128, num_bio_labels))
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls_output = outputs.last_hidden_state[:, 0, :]
        return self.income_head(cls_output), self.description_head(outputs.last_hidden_state)

class MultiTaskLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.ce_inc = nn.CrossEntropyLoss()
        self.ce_bio = nn.CrossEntropyLoss(ignore_index=-100)

    def forward(self, p_inc, p_bio, t_inc, t_bio, mask):
        l_inc = self.ce_inc(p_inc, t_inc)
        t_bio_masked = t_bio.clone()
        t_bio_masked[mask == 0] = -100
        l_bio = self.ce_bio(p_bio.view(-1, 3), t_bio_masked.view(-1))
        return l_inc + l_bio

class FinanceDataset(Dataset):
    def __init__(self, data_path, tokenizer, max_length=64):
        with open(data_path, "r", encoding="utf-8") as f: self.data = json.load(f)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self): return len(self.data)

    def _create_bio_labels(self, text, description, encoding):
        labels = [0] * self.max_length
        t_low, d_low = text.lower(), description.lower()
        start = t_low.find(d_low)
        if start != -1:
            end = start + len(d_low)
            first = True
            for i in range(self.max_length):
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
            "is_income": torch.tensor(int(s["is_income"]), dtype=torch.long),
            "bio_labels": torch.tensor(bio, dtype=torch.long)
        }

def train():
    c = TrainConfig()
    print(f"🚀 Обучение (Только текст) на {c.device}...")
    tokenizer = AutoTokenizer.from_pretrained(c.pretrained_model_name)
    train_ds = FinanceDataset(os.path.join(BASE_DIR, "data", "dataset_train.json"), tokenizer, c.max_seq_length)
    train_loader = DataLoader(train_ds, batch_size=c.batch_size, shuffle=True)
    
    model = FinanceNLPModel(c.pretrained_model_name).to(c.device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=c.learning_rate)
    scheduler = get_linear_schedule_with_warmup(optimizer, int(len(train_loader)*c.num_epochs*c.warmup_ratio), len(train_loader)*c.num_epochs)
    criterion = MultiTaskLoss()
    scaler = torch.amp.GradScaler('cuda', enabled=(c.fp16 and c.device == "cuda"))

    for epoch in range(c.num_epochs):
        model.train()
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}")
        for b in pbar:
            optimizer.zero_grad()
            ids, mask = b["input_ids"].to(c.device), b["attention_mask"].to(c.device)
            with torch.amp.autocast('cuda', enabled=(c.fp16 and c.device == "cuda")):
                p_inc, p_bio = model(ids, mask)
                loss = criterion(p_inc, p_bio, b["is_income"].to(c.device), b["bio_labels"].to(c.device), mask)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            pbar.set_postfix(loss=f"{loss.item():.4f}")

    save_path = os.path.join(PROJECT_DIR, "backend", "app", "ml", "trained_models", "nlp_parser")
    os.makedirs(save_path, exist_ok=True)
    torch.save({"model_state_dict": model.state_dict(), "config": {"pretrained_model_name": c.pretrained_model_name, "num_bio_labels": 3, "max_seq_length": c.max_seq_length}}, os.path.join(save_path, "checkpoint.pt"))
    tokenizer.save_pretrained(os.path.join(save_path, "tokenizer"))
    print(f"✅ Обучение завершено. Модель сохранена.")

if __name__ == "__main__":
    train()
