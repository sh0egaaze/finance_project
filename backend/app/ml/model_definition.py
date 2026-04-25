import torch
import torch.nn as nn
from transformers import AutoModel

class FinanceNLPModel(nn.Module):
    def __init__(self, pretrained_model_name: str, num_bio_labels: int = 3):
        super().__init__()
        self.bert = AutoModel.from_pretrained(pretrained_model_name)
        hidden_size = self.bert.config.hidden_size
        self.amount_head = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(hidden_size, 256),
            nn.GELU(),
            nn.Linear(256, 1)
        )
        self.income_head = nn.Sequential(
            nn.Dropout(0.1),
            nn.Linear(hidden_size, 128),
            nn.GELU(),
            nn.Linear(128, 2)
        )
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
        amount_pred = self.amount_head(cls_output)
        income_logits = self.income_head(cls_output)
        bio_logits = self.description_head(sequence_output)
        return amount_pred, income_logits, bio_logits
