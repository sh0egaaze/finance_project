# ml_training/train_rubert.py

import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))
sys.path.insert(0, PROJECT_DIR)

import json
import torch
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup,
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from tqdm import tqdm
import re
import warnings
warnings.filterwarnings("ignore")

DATA_PATH = os.path.join(BASE_DIR, "data", "transactions.csv")

# Сохраняем в оба места: архив и бэкенд
MODEL_DIRS = [
    os.path.join(BASE_DIR, "trained_models", "rubert"),
    os.path.join(PROJECT_DIR, "backend", "app", "ml", "trained_models", "rubert"),
]


class Config:
    # Варианты моделей:
    # "cointegrated/rubert-tiny2"       — 29M, ~15 мин, accuracy ~97%
    # "ai-forever/ruBert-base"          — 180M, ~45 мин, accuracy ~99%
    # "DeepPavlov/rubert-base-cased"    — 180M, ~45 мин, accuracy ~99%
    MODEL_NAME = "cointegrated/rubert-tiny2"

    BATCH_SIZE = 128        # RTX 5060 Ti 16GB легко тянет
    LEARNING_RATE = 2e-5
    NUM_EPOCHS = 10
    MAX_LENGTH = 64         # Описания транзакций короткие
    WARMUP_RATIO = 0.1
    WEIGHT_DECAY = 0.01
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    SEED = 42
    NUM_WORKERS = 4


def set_seed(seed: int):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    np.random.seed(seed)


def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\b\d{4,}\b", "", text)
    text = re.sub(r"[^\w\s\.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class TransactionDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length: int):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            str(self.texts[idx]),
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(),
            "attention_mask": encoding["attention_mask"].squeeze(),
            "label": torch.tensor(self.labels[idx], dtype=torch.long),
        }


def save_to_dirs(model, tokenizer, artifacts: dict, dirs: list):
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        model.save_pretrained(d)
        tokenizer.save_pretrained(d)
        for filename, data in artifacts.items():
            with open(os.path.join(d, filename), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"   💾 Сохранено: {d}")


def train():
    config = Config()
    set_seed(config.SEED)

    print("=" * 60)
    print("  ОБУЧЕНИЕ RuBERT — КАТЕГОРИЗАТОР ТРАНЗАКЦИЙ")
    print("=" * 60)
    print(f"\n  Устройство : {config.DEVICE}")
    print(f"  Модель     : {config.MODEL_NAME}")

    if config.DEVICE == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1024 ** 3
        print(f"  GPU        : {gpu_name} ({gpu_mem:.1f} GB)")
        print(f"  Batch size : {config.BATCH_SIZE}")
    else:
        print("\n⚠️  CUDA не найдена! Обучение на CPU займёт много времени.")
        answer = input("   Продолжить? (y/n): ")
        if answer.lower() != "y":
            return

    # ----------------------------------------------------------
    # 1. Загрузка данных
    # ----------------------------------------------------------
    print(f"\n[1/6] Загрузка данных...")
    if not os.path.exists(DATA_PATH):
        print(f"❌ Файл не найден: {DATA_PATH}")
        print("   Сначала запусти: python ml_training/data/generate_dataset.py")
        return

    df = pd.read_csv(DATA_PATH, encoding="utf-8")
    df["processed"] = df["description"].apply(preprocess_text)
    df = df[df["processed"].str.len() > 0].reset_index(drop=True)
    print(f"   Загружено : {len(df):,} записей")
    print(f"   Категорий : {df['category'].nunique()}")

    # ----------------------------------------------------------
    # 2. Кодирование категорий
    # ----------------------------------------------------------
    print("\n[2/6] Кодирование категорий...")
    categories = sorted(df["category"].unique().tolist())
    cat2id = {cat: idx for idx, cat in enumerate(categories)}
    id2cat = {idx: cat for cat, idx in cat2id.items()}
    num_labels = len(categories)

    category_names = {}
    for _, row in df[["category", "category_name"]].drop_duplicates().iterrows():
        category_names[row["category"]] = row["category_name"]

    df["label"] = df["category"].map(cat2id)
    print(f"   Категорий : {num_labels}")
    for cat in categories:
        name = category_names[cat]
        count = (df["category"] == cat).sum()
        print(f"   [{cat2id[cat]:2d}] {cat:20s} ({name:25s}) : {count:6,}")

    # ----------------------------------------------------------
    # 3. Train / Test split
    # ----------------------------------------------------------
    print("\n[3/6] Train/Test разделение (80% / 20%)...")
    X_train, X_test, y_train, y_test = train_test_split(
        df["processed"].values,
        df["label"].values,
        test_size=0.2,
        random_state=config.SEED,
        stratify=df["label"].values,
    )
    print(f"   Train : {len(X_train):,}")
    print(f"   Test  : {len(X_test):,}")

    # ----------------------------------------------------------
    # 4. Токенизатор и модель
    # ----------------------------------------------------------
    print(f"\n[4/6] Загрузка {config.MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(config.MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.MODEL_NAME,
        num_labels=num_labels,
        ignore_mismatched_sizes=True,
    )
    model.to(config.DEVICE)

    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"   Всего параметров    : {total_params:,}")
    print(f"   Обучаемых параметров: {trainable_params:,}")

    # ----------------------------------------------------------
    # 5. DataLoaders
    # ----------------------------------------------------------
    print("\n[5/6] Создание DataLoaders...")
    train_loader = DataLoader(
        TransactionDataset(X_train, y_train, tokenizer, config.MAX_LENGTH),
        batch_size=config.BATCH_SIZE,
        shuffle=True,
        num_workers=config.NUM_WORKERS,
        pin_memory=True,
    )
    test_loader = DataLoader(
        TransactionDataset(X_test, y_test, tokenizer, config.MAX_LENGTH),
        batch_size=config.BATCH_SIZE * 2,
        shuffle=False,
        num_workers=config.NUM_WORKERS,
        pin_memory=True,
    )
    print(f"   Train batches : {len(train_loader)}")
    print(f"   Test  batches : {len(test_loader)}")

    # ----------------------------------------------------------
    # 6. Обучение
    # ----------------------------------------------------------
    print("\n[6/6] Обучение...")
    print("-" * 60)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=config.LEARNING_RATE,
        weight_decay=config.WEIGHT_DECAY,
    )

    total_steps = len(train_loader) * config.NUM_EPOCHS
    warmup_steps = int(total_steps * config.WARMUP_RATIO)

    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    use_amp = config.DEVICE == "cuda"
    scaler = torch.amp.GradScaler("cuda") if use_amp else None

    best_accuracy = 0.0
    best_epoch = 0
    train_losses = []
    val_accuracies = []

    for epoch in range(config.NUM_EPOCHS):

        # ---- TRAIN ----
        model.train()
        total_loss = 0.0
        num_batches = 0

        pbar = tqdm(
            train_loader,
            desc=f"Epoch {epoch+1}/{config.NUM_EPOCHS} [Train]",
            leave=True,
        )

        for batch in pbar:
            input_ids = batch["input_ids"].to(config.DEVICE)
            attention_mask = batch["attention_mask"].to(config.DEVICE)
            labels = batch["label"].to(config.DEVICE)

            optimizer.zero_grad()

            if use_amp:
                with torch.amp.autocast("cuda"):
                    outputs = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels,
                    )
                    loss = outputs.loss
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )
                loss = outputs.loss
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()

            scheduler.step()
            total_loss += loss.item()
            num_batches += 1

            pbar.set_postfix({
                "loss": f"{total_loss / num_batches:.4f}",
                "lr": f"{scheduler.get_last_lr()[0]:.2e}",
            })

        avg_loss = total_loss / num_batches
        train_losses.append(avg_loss)

        # ---- EVAL ----
        model.eval()
        all_preds = []
        all_labels_list = []

        with torch.no_grad():
            for batch in tqdm(
                test_loader,
                desc=f"Epoch {epoch+1}/{config.NUM_EPOCHS} [Eval ]",
                leave=True,
            ):
                input_ids = batch["input_ids"].to(config.DEVICE)
                attention_mask = batch["attention_mask"].to(config.DEVICE)

                if use_amp:
                    with torch.amp.autocast("cuda"):
                        outputs = model(
                            input_ids=input_ids,
                            attention_mask=attention_mask,
                        )
                else:
                    outputs = model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                    )

                preds = torch.argmax(outputs.logits, dim=-1)
                all_preds.extend(preds.cpu().numpy())
                all_labels_list.extend(batch["label"].numpy())

        accuracy = accuracy_score(all_labels_list, all_preds)
        val_accuracies.append(accuracy)

        print(f"\n  📊 Epoch {epoch+1:2d} | Loss: {avg_loss:.4f} | Accuracy: {accuracy:.4f}")

        # Сохраняем лучшую модель
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_epoch = epoch + 1

            artifacts = {
                "cat2id.json": cat2id,
                "id2cat.json": {str(k): v for k, v in id2cat.items()},
                "category_names.json": category_names,
                "metadata.json": {
                    "model_name": config.MODEL_NAME,
                    "model_type": "rubert",
                    "best_epoch": epoch + 1,
                    "best_accuracy": float(accuracy),
                    "num_epochs": config.NUM_EPOCHS,
                    "batch_size": config.BATCH_SIZE,
                    "learning_rate": config.LEARNING_RATE,
                    "max_length": config.MAX_LENGTH,
                    "num_categories": num_labels,
                    "train_samples": int(len(X_train)),
                    "test_samples": int(len(X_test)),
                    "train_losses": [float(x) for x in train_losses],
                    "val_accuracies": [float(x) for x in val_accuracies],
                    "version": "1.0.0",
                },
            }

            save_to_dirs(model, tokenizer, artifacts, MODEL_DIRS)
            print(f"  ✅ Лучшая модель сохранена! (Accuracy: {best_accuracy:.4f})")

        print("-" * 60)

    # ----------------------------------------------------------
    # Финальный отчёт
    # ----------------------------------------------------------
    print("\n" + "=" * 60)
    print("  РЕЗУЛЬТАТЫ ОБУЧЕНИЯ")
    print("=" * 60)
    print(f"\n  Лучший epoch   : {best_epoch}")
    print(f"  Лучшая Accuracy: {best_accuracy:.4f}")

    # Загружаем лучшую для финального отчёта
    print("\n  Загрузка лучшей модели для финального отчёта...")
    best_model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIRS[0])
    best_model.to(config.DEVICE)
    best_model.eval()

    all_preds = []
    all_labels_list = []

    with torch.no_grad():
        for batch in tqdm(test_loader, desc="Финальная оценка"):
            input_ids = batch["input_ids"].to(config.DEVICE)
            attention_mask = batch["attention_mask"].to(config.DEVICE)

            if use_amp:
                with torch.amp.autocast("cuda"):
                    outputs = best_model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                    )
            else:
                outputs = best_model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                )

            preds = torch.argmax(outputs.logits, dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_labels_list.extend(batch["label"].numpy())

    target_names = [id2cat[i] for i in range(num_labels)]
    print("\n" + classification_report(
        all_labels_list, all_preds, target_names=target_names
    ))

    # ----------------------------------------------------------
    # Тестовые предсказания
    # ----------------------------------------------------------
    print("=" * 60)
    print("  ТЕСТОВЫЕ ПРЕДСКАЗАНИЯ")
    print("=" * 60)

    tests = [
        ("ПЯТЕРОЧКА №15 Москва",                "food"),
        ("ЯНДЕКС ТАКСИ поездка",                "transport"),
        ("Перевод Петровой А.С. СБП",           "transfers"),
        ("Зарплата за апрель ООО Яндекс",       "salary"),
        ("Wildberries заказ одежда",            "shopping"),
        ("Аптека Горздрав лекарства",           "health"),
        ("KFC бургер картошка",                 "restaurants"),
        ("Netflix подписка",                    "entertainment"),
        ("Штраф ГИБДД превышение скорости",    "taxes"),
        ("World Class абонемент фитнес",        "sports"),
        ("МТС оплата мобильная связь",          "telecom"),
        ("Booking.com отель Сочи",              "travel"),
        ("Снятие наличных банкомат ВТБ",        "cash"),
        ("Парикмахерская барбершоп стрижка",   "beauty"),
        ("Skillbox курс Python разработка",    "education"),
        ("Ветеринарная клиника прививка кот",  "pets"),
        ("Яндекс Плюс подписка",               "subscriptions"),
        ("ИНГОССТРАХ КАСКО оплата",            "insurance"),
        ("Ипотека Сбербанк ежемесячный платёж", "housing"),
        ("Пожертвование фонд помощи детям",    "charity"),
    ]

    correct = 0
    for desc, expected in tests:
        processed = preprocess_text(desc)
        enc = tokenizer(
            processed,
            max_length=config.MAX_LENGTH,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        ).to(config.DEVICE)

        with torch.no_grad():
            out = best_model(**enc)
            probs = torch.softmax(out.logits, dim=-1)[0]
            pred_id = torch.argmax(probs).item()
            confidence = probs[pred_id].item()

        pred_cat = id2cat[pred_id]
        pred_name = category_names.get(pred_cat, pred_cat)
        is_correct = pred_cat == expected
        if is_correct:
            correct += 1
        icon = "✅" if is_correct else "❌"

        print(f"\n{icon} '{desc}'")
        print(f"    Ожидалось : {expected}")
        print(f"    Получено  : {pred_cat} ({pred_name}) [{confidence:.1%}]")

    print(f"\n  Правильных на тесте: {correct}/{len(tests)}")
    print(f"\n🎉 Обучение завершено! Модель готова к использованию.")
    print(f"   Модель сохранена в:")
    for d in MODEL_DIRS:
        print(f"   - {d}")


if __name__ == "__main__":
    train()