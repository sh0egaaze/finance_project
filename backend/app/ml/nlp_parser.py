import os
import torch
import re
import difflib
from transformers import AutoTokenizer
from .model_definition import FinanceNLPModel

# Максимально расширенный словарь числительных (включая падежи и сленг)
RUS_NUMBERS = {
    # Единицы и падежи
    'ноль': 0, 'нуль': 0,
    'один': 1, 'одна': 1, 'одну': 1, 'одного': 1, 'одним': 1,
    'два': 2, 'две': 2, 'двух': 2, 'двум': 2, 'двумя': 2,
    'три': 3, 'трех': 3, 'трем': 3, 'тремя': 3,
    'четыре': 4, 'четырех': 4, 'четырем': 4, 'четырьмя': 4,
    'пять': 5, 'пяти': 5, 'пятью': 5,
    'шесть': 6, 'шести': 6, 'шестью': 6,
    'семь': 7, 'семи': 7, 'семью': 7,
    'восемь': 8, 'восьми': 8, 'восемью': 8,
    'девять': 9, 'девяти': 9, 'девятью': 9,
    
    # Подростки
    'десять': 10, 'десяти': 10,
    'одиннадцать': 11, 'двенадцать': 12, 'тринадцать': 13, 'четырнадцать': 14,
    'пятнадцать': 15, 'шестнадцать': 16, 'семнадцать': 17, 'восемнадцать': 18, 'девятнадцать': 19,
    
    # Десятки
    'двадцать': 20, 'двадцати': 20,
    'тридцать': 30, 'тридцати': 30,
    'сорок': 40, 'сорока': 40,
    'пятьдесят': 50, 'пятидесяти': 50,
    'шестьдесят': 60, 'шестидесяти': 60,
    'семьдесят': 70, 'семидесяти': 70,
    'восемьдесят': 80, 'восьмидесяти': 80,
    'девяносто': 90, 'девяноста': 90,
    
    # Сотни
    'сто': 100, 'ста': 100,
    'двести': 200, 'двухсот': 200, 'двумстам': 200,
    'триста': 300, 'трехсот': 300, 'тремстам': 300,
    'четыреста': 400, 'четырехсот': 400, 'четыремстам': 400,
    'пятьсот': 500, 'шестьсот': 600, 'семьсот': 700, 'восемьсот': 800, 'девятьсот': 900,
    
    # Тысячи и сленг
    'тысяча': 1000, 'тысячи': 1000, 'тысяч': 1000, 'тыщу': 1000, 'тыщей': 1000,
    'косарь': 1000, 'косаря': 1000, 'косарей': 1000, 'кес': 1000, 'к': 1000,
    'штука': 1000, 'штуки': 1000, 'штук': 1000,
    
    # Миллионы
    'миллион': 1000000, 'миллиона': 1000000, 'миллионов': 1000000, 'лям': 1000000, 'ляма': 1000000, 'лямов': 1000000,
}

class FinanceParser:
    def __init__(self, model_dir: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint_path = os.path.join(model_dir, "checkpoint.pt")
        tokenizer_path = os.path.join(model_dir, "tokenizer")
        
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        
        conf = checkpoint["config"]
        self.model = FinanceNLPModel(conf["pretrained_model_name"], conf["num_bio_labels"])
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()
        self.max_length = conf["max_seq_length"]
        
        # Список всех эталонных слов для коррекции опечаток
        self.vocab_words = list(RUS_NUMBERS.keys())
        
        self._typo_cache: dict[str, str | None] = {}

    def _fix_typos(self, word: str):
        """Исправляет опечатки в словах-числах (с кэшированием)"""
        if word in self._typo_cache:
            return self._typo_cache[word]
        
        if word in RUS_NUMBERS:
            self._typo_cache[word] = word
            return word
        # Ищем максимально похожее слово (точность 80%)
        matches = difflib.get_close_matches(word, self.vocab_words, n=1, cutoff=0.8)
        result = matches[0] if matches else None
        self._typo_cache[word] = result
        return result

    def _words_to_num(self, text: str):
        """Продвинутая конвертация текста в число"""
        # Чистим текст от знаков препинания
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        
        total = 0
        current = 0
        found = False
        
        for w in words:
            # 1. Проверяем сокращения типа "5к" или "1.5лям"
            short_match = re.match(r'(\d+[\.,]?\d*)(к|лям|косаря|штуки)', w)
            if short_match:
                val = float(short_match.group(1).replace(",", "."))
                multiplier = 1000 if short_match.group(2) == 'к' or 'штук' in short_match.group(2) else 1000000
                total += val * multiplier
                found = True
                continue

            # 2. Пытаемся найти слово в словаре (с учетом опечаток)
            fixed_w = self._fix_typos(w)
            if fixed_w and fixed_w in RUS_NUMBERS:
                found = True
                val = RUS_NUMBERS[fixed_w]
                if val >= 1000:
                    if current == 0: current = 1
                    total += current * val
                    current = 0
                else:
                    current += val
        
        total += current
        return float(total) if found else None

    def _extract_amount(self, text: str):
        """Приоритет извлечения: Цифры -> Текст"""
        # 1. Ищем явные числа (например '150.50' или '1 500')
        text_no_spaces = re.sub(r'(?<=\d)\s(?=\d)', '', text)
        match = re.search(r'(\d+[\.,]?\d*)', text_no_spaces)
        if match:
            try:
                amt = float(match.group(1).replace(",", "."))
                text_lower = text.lower()
                text_words = text_lower.split()
                if amt < 1000:
                    if any(w in text_words for w in ['тысяча', 'тысячи', 'тысяч', 'тыщу', 'тыщей', 'косарь', 'косаря', 'косарей', 'кес', 'к', 'штука', 'штуки', 'штук']):
                        return amt * 1000
                    if any(w in text_words for w in ['миллион', 'миллиона', 'миллионов', 'лям', 'ляма']):
                        return amt * 1000000
                return amt
            except: pass
        
        # 2. Ищем словами
        return self._words_to_num(text)

    def _extract_description_from_bio(self, tokens, bio_preds, attention_mask):
        description_tokens = []
        in_description = False
        for i, (token, bio, mask) in enumerate(zip(tokens, bio_preds, attention_mask)):
            if mask == 0: break
            if bio == 1: # B-DESC
                in_description = True
                description_tokens.append(token)
            elif bio == 2 and in_description: # I-DESC
                description_tokens.append(token)
            else:
                if in_description: break
        return self.tokenizer.convert_tokens_to_string(description_tokens).strip()

    def parse(self, text: str) -> dict:
        # Извлекаем сумму
        amount = self._extract_amount(text) or 0.0

        # AI инференс для описания и типа
        encoding = self.tokenizer(text, max_length=self.max_length, padding="max_length", truncation=True, return_tensors="pt")
        ids, mask = encoding["input_ids"].to(self.device), encoding["attention_mask"].to(self.device)
        
        with torch.no_grad():
            inc_logits, bio_logits = self.model(ids, mask)
        
        bio_preds = bio_logits.argmax(dim=-1).squeeze().cpu().tolist()
        tokens = self.tokenizer.convert_ids_to_tokens(ids.squeeze().cpu().tolist())
        description = self._extract_description_from_bio(tokens, bio_preds, mask.squeeze().cpu().tolist())
        is_income = torch.argmax(inc_logits, dim=-1).item() == 1

        return {
            "amount": amount,
            "description": description or text,
            "is_income": is_income,
            "confidence": "high (fuzzy-logic)"
        }