import React, { useState, useEffect } from 'react';
import { Search, Edit2, Trash2, RefreshCw, Loader2, AlertTriangle, Building2, ChevronDown, ChevronUp } from 'lucide-react';
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
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  const cardClass = "bg-white rounded-xl shadow-sm border border-gray-100 dark:bg-gray-800 dark:border-gray-700";
  const inputClass = "px-3 sm:px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400 text-sm sm:text-base";
  const titleClass = "text-gray-900 dark:text-white";

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

  const getCategoryName = (categoryId: number | null) => {
    if (!categoryId) return 'Без категории';
    const cat = categories.find(c => c.id === categoryId);
    return cat?.name || 'Без категории';
  };

  const getCategoryIcon = (categoryId: number | null) => {
    if (!categoryId) return '•';
    const cat = categories.find(c => c.id === categoryId);
    return cat?.icon || '•';
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

  const filteredTransactions = transactions.filter(tx => {
    if (searchQuery && !tx.description?.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (selectedCategory) {
      const cat = categories.find(c => c.code === selectedCategory);
      if (!cat || tx.category_id !== cat.id) return false;
    }
    if (selectedSource && (!tx.source || tx.source !== selectedSource)) return false;
    if (dateFrom && tx.transaction_date && new Date(tx.transaction_date) < new Date(dateFrom)) return false;
    if (dateTo && tx.transaction_date) {
      const to = new Date(dateTo);
      to.setHours(23, 59, 59, 999);
      if (new Date(tx.transaction_date) > to) return false;
    }
    return true;
  });

  const groupedTransactions = filteredTransactions.reduce((acc, tx) => {
    const date = tx.transaction_date ? new Date(tx.transaction_date).toLocaleDateString('ru-RU') : 'Без даты';
    if (!acc[date]) acc[date] = [];
    acc[date].push(tx);
    return acc;
  }, {} as Record<string, Transaction[]>);

  const hasActiveFilters = searchQuery || selectedCategory || selectedSource || dateFrom || dateTo;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center dark:bg-red-900/30 dark:border-red-700">
        <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
        <p className="text-red-700 mb-4 dark:text-red-400">{error}</p>
        <button onClick={loadTransactions} className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600">
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h1 className={`text-xl sm:text-2xl font-bold ${titleClass}`}>Транзакции</h1>
        <button
          onClick={handleSyncTBank}
          disabled={syncing}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 disabled:opacity-50 text-sm sm:text-base"
        >
          {syncing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Building2 className="w-4 h-4" />}
          <span className="hidden xs:inline">Синхронизировать</span> Т-Банк
        </button>
      </div>

      {/* Сообщение синхронизации */}
      {syncMessage && (
        <div className={`p-3 sm:p-4 rounded-lg text-sm ${
          syncMessage.includes('Ошибка') || syncMessage.includes('не подключён')
            ? 'bg-red-50 border border-red-200 text-red-700 dark:bg-red-900/30 dark:border-red-700 dark:text-red-400'
            : 'bg-green-50 border border-green-200 text-green-700 dark:bg-green-900/30 dark:border-green-700 dark:text-green-400'
        }`}>
          {syncMessage}
        </div>
      )}

      {/* Фильтры */}
      <div className={`${cardClass} p-3 sm:p-4`}>
        {/* Поиск + кнопка фильтров */}
        <div className="flex gap-2 sm:gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Поиск..."
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400 text-sm sm:text-base"
            />
          </div>
          <button 
            onClick={() => setShowFilters(!showFilters)}
            className={`px-3 sm:px-4 py-2 border rounded-lg flex items-center gap-1 sm:gap-2 text-sm transition-colors ${
              hasActiveFilters 
                ? 'border-blue-500 bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:border-blue-500 dark:text-blue-400' 
                : 'border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-400 dark:hover:bg-gray-700'
            }`}
          >
            {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            <span className="hidden sm:inline">Фильтры</span>
            {hasActiveFilters && <span className="w-2 h-2 rounded-full bg-blue-500" />}
          </button>
          <button onClick={loadTransactions} className="p-2 hover:bg-gray-100 rounded-lg dark:hover:bg-gray-700 shrink-0">
            <RefreshCw className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>
        
        {/* Расширенные фильтры */}
        {showFilters && (
          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="flex items-center gap-2">
                <input 
                  type="date" 
                  value={dateFrom} 
                  onChange={(e) => setDateFrom(e.target.value)} 
                  className={`flex-1 ${inputClass}`}
                  placeholder="От"
                />
                <span className="text-gray-400">—</span>
                <input 
                  type="date" 
                  value={dateTo} 
                  onChange={(e) => setDateTo(e.target.value)} 
                  className={`flex-1 ${inputClass}`}
                  placeholder="До"
                />
              </div>
              <select value={selectedCategory} onChange={(e) => setSelectedCategory(e.target.value)} className={inputClass}>
                <option value="">Все категории</option>
                {categories.map(cat => <option key={cat.id} value={cat.code}>{cat.name}</option>)}
              </select>
              <select value={selectedSource} onChange={(e) => setSelectedSource(e.target.value)} className={inputClass}>
                <option value="">Все источники</option>
                <option value="manual">Вручную</option>
                <option value="tbank_api">Т-Банк</option>
              </select>
              <button
                onClick={() => { setSearchQuery(''); setSelectedCategory(''); setSelectedSource(''); setDateFrom(''); setDateTo(''); }}
                className="px-3 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors dark:text-gray-300 dark:border-gray-600 dark:hover:bg-gray-700"
              >
                Сбросить
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Список транзакций */}
      <div className="space-y-3 sm:space-y-4">
        {Object.keys(groupedTransactions).length === 0 ? (
          <div className={`${cardClass} p-8 text-center`}>
            <p className="text-gray-500 dark:text-gray-400">Нет транзакций</p>
            <p className="text-sm text-gray-400 mt-2 dark:text-gray-500">
              Добавьте транзакцию через кнопку &quot;+ Добавить&quot; или синхронизируйте Т-Банк
            </p>
          </div>
        ) : (
          Object.entries(groupedTransactions).map(([date, txs]) => (
            <div key={date} className={cardClass}>
              <div className="px-3 sm:px-4 py-2 sm:py-3 border-b bg-gray-50 rounded-t-xl dark:bg-gray-700 dark:border-gray-600">
                <span className="font-medium text-sm sm:text-base text-gray-700 dark:text-gray-300">{date}</span>
              </div>
              <div className="divide-y dark:divide-gray-700">
                {txs.map(tx => (
                  <div key={tx.id} className="px-3 sm:px-4 py-2.5 sm:py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700 gap-2">
                    <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
                      <span className="text-lg sm:text-xl shrink-0" style={{ color: categories.find(c => c.id === tx.category_id)?.color || '#6B7280' }}>
                        {getCategoryIcon(tx.category_id)}
                      </span>
                      <div className="min-w-0">
                        <p className={`font-medium text-sm sm:text-base ${titleClass} truncate`}>{tx.description || 'Без описания'}</p>
                        <div className="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm text-gray-500 dark:text-gray-400">
                          <span className="truncate">{getCategoryName(tx.category_id)}</span>
                          {tx.transaction_date && (
                            <>
                              <span className="hidden xs:inline">·</span>
                              <span className="hidden xs:inline">{new Date(tx.transaction_date).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 sm:gap-2 shrink-0">
                      <span className={`font-semibold text-sm sm:text-base ${tx.is_income ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                        {tx.is_income ? '+' : '-'}{Math.abs(Number(tx.amount)).toLocaleString('ru-RU')} ₽
                      </span>
                      <div className="flex gap-1">
                        <button onClick={() => setEditingTransaction(tx)} className="p-1.5 sm:p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-blue-500 dark:hover:bg-gray-600">
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(tx.id)} className="p-1.5 sm:p-2 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-red-500 dark:hover:bg-gray-600">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
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
