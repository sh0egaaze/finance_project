import React, { useState, useEffect } from 'react';
import { Search, Edit2, Trash2, RefreshCw, Loader2, AlertTriangle, Building2 } from 'lucide-react';
import { api, Transaction, Category } from '../api';
import { EditTransactionModal } from './EditTransactionModal';

interface TransactionsProps {
  categories: Category[];
}

const Transactions: React.FC<TransactionsProps> = ({ categories }) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedSource, setSelectedSource] = useState<string>('');
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const loadTransactions = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await api.getTransactions({ limit: 100 });
      setTransactions(result.items);
    } catch (err) {
      setError('Не удалось загрузить транзакции');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTransactions();
  }, []);

  const handleDelete = async (id: number) => {
    if (!confirm('Удалить транзакцию?')) return;
    
    try {
      await api.deleteTransaction(id);
      setTransactions(prev => prev.filter(t => t.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  const handleSyncTBank = async () => {
    setSyncing(true);
    setSyncMessage(null);
    
    try {
      const result = await api.syncTBank();
      setSyncMessage(result.message);
      await loadTransactions();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const error = err as { response?: { data?: { detail?: string } } };
        setSyncMessage(error.response?.data?.detail || 'Ошибка синхронизации');
      } else {
        setSyncMessage('Ошибка синхронизации');
      }
    } finally {
      setSyncing(false);
    }
  };

  // Фильтрация
  const filteredTransactions = transactions.filter(tx => {
    if (searchQuery && !tx.description?.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    if (selectedCategory && tx.category?.code !== selectedCategory) {
      return false;
    }
    if (selectedSource && tx.source !== selectedSource) {
      return false;
    }
    return true;
  });

  // Группировка по дате
  const groupedTransactions = filteredTransactions.reduce((acc, tx) => {
    const date = new Date(tx.transaction_date).toLocaleDateString('ru-RU');
    if (!acc[date]) acc[date] = [];
    acc[date].push(tx);
    return acc;
  }, {} as Record<string, Transaction[]>);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-700 mb-4">{error}</p>
        <button
          onClick={loadTransactions}
          className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Транзакции</h1>
        <button
          onClick={handleSyncTBank}
          disabled={syncing}
          className="flex items-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50"
        >
          {syncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Building2 className="w-4 h-4" />}
          Синхронизировать Т-Банк
        </button>
      </div>

      {/* Сообщение синхронизации */}
      {syncMessage && (
        <div className={`p-4 rounded-lg ${
          syncMessage.includes('Ошибка') || syncMessage.includes('не подключён') 
            ? 'bg-red-50 border border-red-200 text-red-700' 
            : 'bg-green-50 border border-green-200 text-green-700'
        }`}>
          {syncMessage}
        </div>
      )}

      {/* Фильтры */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
        <div className="flex flex-wrap gap-4">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Поиск по описанию..."
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Все категории</option>
            {categories.map(cat => (
              <option key={cat.id} value={cat.code}>{cat.name}</option>
            ))}
          </select>
          
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Все источники</option>
            <option value="manual">Вручную</option>
            <option value="tbank_api">Т-Банк</option>
          </select>

          <button
            onClick={loadTransactions}
            className="p-2 hover:bg-gray-100 rounded-lg"
          >
            <RefreshCw className="w-5 h-5 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Список транзакций */}
      <div className="space-y-4">
        {Object.keys(groupedTransactions).length === 0 ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8 text-center">
            <p className="text-gray-500">Нет транзакций</p>
            <p className="text-sm text-gray-400 mt-2">
              Добавьте транзакцию через кнопку "+ Добавить" или синхронизируйте Т-Банк
            </p>
          </div>
        ) : (
          Object.entries(groupedTransactions).map(([date, txs]) => (
            <div key={date} className="bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="px-4 py-3 border-b bg-gray-50 rounded-t-xl">
                <span className="font-medium text-gray-700">{date}</span>
              </div>
              <div className="divide-y">
                {txs.map(tx => (
                  <div key={tx.id} className="px-4 py-3 flex items-center justify-between hover:bg-gray-50">
                    <div className="flex items-center gap-3">
                      {tx.category && (
                        <div
                          className="w-10 h-10 rounded-full flex items-center justify-center"
                          style={{ backgroundColor: (tx.category.color || '#6B7280') + '20' }}
                        >
                          <span style={{ color: tx.category.color || '#6B7280' }}>
                            {tx.category.icon?.charAt(0).toUpperCase() || '•'}
                          </span>
                        </div>
                      )}
                      <div>
                        <p className="font-medium text-gray-900">{tx.description || 'Без описания'}</p>
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                          <span>{tx.category?.name || 'Без категории'}</span>
                          {tx.source === 'tbank_api' && (
                            <span className="px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded text-xs">
                              Т-Банк
                            </span>
                          )}
                          {tx.is_suspicious && (
                            <span className="px-1.5 py-0.5 bg-red-100 text-red-700 rounded text-xs">
                              Подозрительная
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      <span className={`font-semibold ${Number(tx.amount) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {Number(tx.amount) >= 0 ? '+' : ''}{Number(tx.amount).toLocaleString('ru-RU')} ₽
                      </span>
                      
                      <button
                        onClick={() => setEditingTransaction(tx)}
                        className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-blue-500"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      
                      <button
                        onClick={() => handleDelete(tx.id)}
                        className="p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-red-500"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Модалка редактирования */}
      {editingTransaction && (
        <EditTransactionModal
          transaction={editingTransaction}
          onClose={() => setEditingTransaction(null)}
          onSaved={loadTransactions}
        />
      )}
    </div>
  );
};

export default Transactions;
