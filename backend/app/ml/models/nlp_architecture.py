import torch
import torch.nn as nn
from transformers import AutoModel

class FinanceNLPModel(nn.Module):
    def __init__(self, pretrained_model_name: str = "DeepPavlov/rubert-base-cased"):
        super().__init__()
        self.bert = AutoModel.from_pretrained(pretrained_model_name)
        hidden_size = self.bert.config.hidden_size
        self.amount_head = nn.Linear(hidden_size, 1)
        self.income_head = nn.Linear(hidden_size, 2)
        self.description_head = nn.Linear(hidden_size, 3) # BIO labels
    
    def forward(self, input_ids, attention_mask):
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        cls_output = outputs.last_hidden_state[:, 0, :]
        sequence_output = outputs.last_hidden_state
        return self.amount_head(cls_output), self.income_head(cls_output), self.description_head(sequence_output)
