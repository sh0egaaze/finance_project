import torch
import torch.nn as nn

class TransactionAutoencoder(nn.Module):
    def __init__(self, input_dim, hidden_dims=[64, 32, 16], encoding_dim=8):
        super().__init__()
        layers = []
        prev = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
            prev = h
        layers.append(nn.Linear(prev, encoding_dim))
        self.encoder = nn.Sequential(*layers)
        
        layers = []
        prev = encoding_dim
        for h in reversed(hidden_dims):
            layers.append(nn.Linear(prev, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
            prev = h
        layers.append(nn.Linear(prev, input_dim))
        self.decoder = nn.Sequential(*layers)

    def forward(self, x):
        return self.decoder(self.encoder(x))

    def get_error(self, x):
        self.eval()
        with torch.no_grad():
            return torch.mean((x - self.forward(x))**2, dim=1)
