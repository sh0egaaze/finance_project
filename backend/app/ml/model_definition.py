import torch
import torch.nn as nn
from transformers import AutoModel

class FinanceNLPModel(nn.Module):
    """
    NLP Модель (Версия 2.0 - Только текст).
    Убрали предсказание суммы, чтобы сосредоточиться на BIO-тегах и классификации.
    """
    def __init__(self, pretrained_model_name: str, num_bio_labels: int = 3):
        super().__init__()
        self.bert = AutoModel.from_pretrained(pretrained_model_name)
        hidden_size = self.bert.config.hidden_size
        
        # Доход/Расход
        self.income_head = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(hidden_size, 128),
            nn.GELU(),
            nn.Linear(128, 2)
        )
        
        # Описание (BIO)
        self.description_head = nn.Sequential(
            nn.Dropout(0.1),
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
    """Продвинутый VAE для детекции аномалий"""
    def __init__(self, input_dim, hidden_dim=64, latent_dim=8):
        super().__init__()
        self.input_dim = input_dim
        
        # Encoder
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.GELU()
        )
        
        # Latent space (mu and logvar)
        self.fc_mu = nn.Linear(hidden_dim // 2, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim // 2, latent_dim)
        
        # Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, input_dim)
        )

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        return self.decoder(z), mu, logvar

    def get_reconstruction_error(self, x):
        self.eval()
        with torch.no_grad():
            recon, mu, logvar = self.forward(x)
            return torch.mean((x - recon)**2, dim=1)
