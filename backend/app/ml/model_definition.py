import torch
import torch.nn as nn
from transformers import AutoModel


class FinanceNLPModel(nn.Module):
    """
    NLP Модуль (Версия 2.0 - поддержка токизации).
    Объединённый ресурсы, читает тексты и распознаёт
    дополнительные БИО-теги и категоризации.
    """
    def __init__(self, pretrained_model_name: str, num_bio_labels: int = 11):  
        super().__init__()
        self.bert = AutoModel.from_pretrained(pretrained_model_name)
        hidden_size = self.bert.config.hidden_size
        
        # Доход/расход (УБРАЛ Dropout)
        self.income_head = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.GELU(),
            nn.Linear(128, 2)
        )
        
        # Описание (BIO) (УБРАЛ Dropout)
        self.description_head = nn.Sequential(
            nn.Linear(hidden_size, 128),
            nn.GELU(),
            nn.Linear(128, num_bio_labels)
        )
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls_output = outputs.last_hidden_state[:, 0, :]
        sequence_output = outputs.last_hidden_state
        
        income_logits = self.income_head(cls_output)
        bio_logits = self.description_head(sequence_output)
        
        return income_logits, bio_logits

class TransactionAutoencoder(nn.Module):
    """VAE для детекции аномалий в транзакциях"""
    def __init__(self, input_dim, hidden=48, latent=10):
        super().__init__()
        self.input_dim = input_dim
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.BatchNorm1d(hidden),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden, hidden // 2),
            nn.GELU(),
        )
        
        self.fc_mu     = nn.Linear(hidden // 2, latent)
        self.fc_logvar = nn.Linear(hidden // 2, latent)
        
        self.decoder = nn.Sequential(
            nn.Linear(latent, hidden // 2),
            nn.GELU(),
            nn.Linear(hidden // 2, hidden),
            nn.BatchNorm1d(hidden),
            nn.GELU(),
            nn.Linear(hidden, input_dim),
        )

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        return mu + torch.randn_like(std) * std

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        return self.decoder(z), mu, logvar