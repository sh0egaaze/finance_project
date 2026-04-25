import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, XCircle, Eye } from 'lucide-react';
import { api, Transaction } from '../api';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
  }).format(Math.abs(value));
};

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short',
  });
};

export default function SuspiciousTransactions() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadSuspicious = async () => {
    try {
      const data = await api.getTransactions({ is_suspicious: true, limit: 50 });
      setTransactions(data.items);
    } catch (error) {
      console.error('Error loading suspicious transactions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSuspicious();
  }, []);

  const handleConfirm = async (id: number) => {
    try {
      await api.updateTransaction(id, { is_suspicious: false });
      setTransactions(transactions.filter(t => t.id !== id));
    } catch (error) {
      console.error('Error confirming transaction:', error);
    }
  };

  const handleReject = async (id: number) => {
    try {
      await api.deleteTransaction(id);
      setTransactions(transactions.filter(t => t.id !== id));
    } catch (error) {
      console.error('Error rejecting transaction:', error);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Подозрительные транзакции</h2>
        {transactions.length > 0 && (
          <span className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-sm">
            {transactions.length} найдено
          </span>
        )}
      </div>

      {/* Info Card */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-yellow-800">Как определяются подозрительные транзакции?</h3>
            <ul className="text-sm text-yellow-700 mt-2 space-y-1">
              <li>• Сумма значительно выше обычной для категории</li>
              <li>• Необычное время совершения</li>
              <li>• Новый продавец с большой суммой</li>
              <li>• Несколько похожих транзакций подряд</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Transactions List */}
      {transactions.length === 0 ? (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
          <p className="text-gray-600 font-medium">Всё в порядке!</p>
          <p className="text-gray-400 text-sm mt-2">Подозрительных транзакций не обнаружено</p>
        </div>
      ) : (
        <div className="space-y-4">
          {transactions.map((transaction) => (
            <div
              key={transaction.id}
              className="bg-white rounded-xl shadow-sm p-6 border-l-4 border-red-500"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-red-100 rounded-lg">
                    <AlertTriangle className="w-6 h-6 text-red-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-800">
                      {transaction.description || 'Без описания'}
                    </h3>
                    <p className="text-sm text-gray-500 mt-1">
                      {transaction.merchant_name || transaction.category?.name || 'Неизвестная категория'}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {formatDate(transaction.transaction_date)}
                    </p>
                    {transaction.suspicious_reason && (
                      <p className="text-sm text-red-600 mt-2 flex items-center gap-1">
                        <Eye className="w-4 h-4" />
                        {transaction.suspicious_reason}
                      </p>
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xl font-bold text-red-600">
                    -{formatCurrency(transaction.amount)}
                  </p>
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => handleConfirm(transaction.id)}
                      className="flex items-center gap-1 px-3 py-1.5 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors"
                      title="Это моя транзакция"
                    >
                      <CheckCircle className="w-4 h-4" />
                      <span className="text-sm">Подтвердить</span>
                    </button>
                    <button
                      onClick={() => handleReject(transaction.id)}
                      className="flex items-center gap-1 px-3 py-1.5 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
                      title="Это не моя транзакция"
                    >
                      <XCircle className="w-4 h-4" />
                      <span className="text-sm">Оспорить</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
