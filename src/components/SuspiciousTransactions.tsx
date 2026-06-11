import { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, XCircle, Eye, RefreshCw } from 'lucide-react';
import { api, Category } from '../api';

interface SuspiciousTransaction {
  id: number;
  description: string;
  amount: number;
  category_id: number | null;
  transaction_date: string | null;
  suspicious_reason?: string;
}

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 0 }).format(Math.abs(value));
};

const formatDate = (dateString: string | null) => {
  if (!dateString) return '—';
  return new Date(dateString).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
};

function ConfirmModal({ 
  isOpen, 
  onClose, 
  onConfirm, 
  title, 
  message, 
  confirmText = "Подтвердить",
  confirmColor = "blue"
}: {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  confirmColor?: "blue" | "green" | "red";
}) {
  if (!isOpen) return null;

  const colorClasses = {
    blue: "bg-blue-600 hover:bg-blue-700",
    green: "bg-green-600 hover:bg-green-700",
    red: "bg-red-600 hover:bg-red-700",
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-semibold text-gray-800 dark:text-white mb-2">{title}</h3>
        <p className="text-sm text-gray-600 dark:text-gray-300 mb-4 sm:mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button
            onClick={onClose}
            className="px-3 sm:px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors dark:text-gray-400 dark:hover:bg-gray-700"
          >
            Отмена
          </button>
          <button
            onClick={() => { onConfirm(); onClose(); }}
            className={`px-3 sm:px-4 py-2 text-sm text-white rounded-lg transition-colors ${colorClasses[confirmColor]}`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function SuspiciousTransactions() {
  const [transactions, setTransactions] = useState<SuspiciousTransaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [reportedIds, setReportedIds] = useState<Set<number>>(new Set());
  
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    transactionId: number | null;
    type: 'dismiss' | 'report' | 'remove';
  }>({ isOpen: false, transactionId: null, type: 'dismiss' });

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [txData, catData] = await Promise.all([
        api.getTransactions({ is_suspicious: true, limit: 50 }),
        api.getCategories()
      ]);
      setTransactions(txData.items);
      setCategories(catData);
    } catch (error) {
      console.error('Error loading suspicious transactions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const getCategoryName = (categoryId: number | null): string => {
    if (!categoryId) return 'Без категории';
    const category = categories.find(c => c.id === categoryId);
    return category?.name || 'Без категории';
  };

  const handleConfirmDismiss = async () => {
    if (!confirmModal.transactionId) return;
    try {
      await api.dismissSuspicious(confirmModal.transactionId);
      setTransactions(transactions.filter(t => t.id !== confirmModal.transactionId));
    } catch (error) {
      console.error('Error dismissing transaction:', error);
      alert('Ошибка при подтверждении транзакции');
    }
  };

  const handleConfirmReport = () => {
    if (!confirmModal.transactionId) return;
    setReportedIds(prev => new Set(prev).add(confirmModal.transactionId!));
  };

  const handleRemoveFromList = async () => {
    if (!confirmModal.transactionId) return;
    try {
      await api.dismissSuspicious(confirmModal.transactionId);
      setTransactions(transactions.filter(t => t.id !== confirmModal.transactionId));
      setReportedIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(confirmModal.transactionId!);
        return newSet;
      });
    } catch (error) {
      console.error('Error removing transaction:', error);
    }
  };

  const openConfirmModal = (transactionId: number, type: 'dismiss' | 'report' | 'remove') => {
    setConfirmModal({ isOpen: true, transactionId, type });
  };

  const closeConfirmModal = () => {
    setConfirmModal({ isOpen: false, transactionId: null, type: 'dismiss' });
  };

  const getModalProps = () => {
    const tx = transactions.find(t => t.id === confirmModal.transactionId);
    const amount = tx ? formatCurrency(tx.amount) : '';

    switch (confirmModal.type) {
      case 'dismiss':
        return {
          title: "Подтвердить транзакцию?",
          message: `Вы уверены, что транзакция на ${amount} легитимна? Она будет убрана из списка подозрительных.`,
          confirmText: "Да, всё в порядке",
          confirmColor: "green" as const,
          onConfirm: handleConfirmDismiss,
        };
      case 'report':
        return {
          title: "Сообщить о подозрительной транзакции?",
          message: `Вы не совершали транзакцию на ${amount}? Мы покажем рекомендуемые действия.`,
          confirmText: "Да, есть подозрения",
          confirmColor: "red" as const,
          onConfirm: handleConfirmReport,
        };
      case 'remove':
        return {
          title: "Убрать из списка?",
          message: "Вы разобрались с этой транзакцией и хотите убрать её из списка подозрительных?",
          confirmText: "Да, убрать",
          confirmColor: "blue" as const,
          onConfirm: handleRemoveFromList,
        };
      default:
        return {
          title: "",
          message: "",
          confirmText: "",
          confirmColor: "blue" as const,
          onConfirm: () => {},
        };
    }
  };

  const cardClass = "bg-white rounded-xl shadow-sm p-4 sm:p-6 dark:bg-gray-800";
  const titleClass = "text-gray-800 dark:text-white";
  const mutedClass = "text-gray-400 dark:text-gray-500";

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400"></div>
      </div>
    );
  }

  const modalProps = getModalProps();

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h2 className={`text-xl sm:text-2xl font-bold ${titleClass}`}>Подозрительные транзакции</h2>
        <div className="flex items-center gap-3">
          {transactions.length > 0 && (
            <span className="bg-red-100 text-red-700 px-3 py-1 rounded-full text-xs sm:text-sm dark:bg-red-900/30 dark:text-red-400">
              {transactions.length} найдено
            </span>
          )}
          <button onClick={loadData} className="p-2 hover:bg-gray-100 rounded-lg transition-colors dark:hover:bg-gray-700">
            <RefreshCw className="w-5 h-5 text-gray-500 dark:text-gray-400" />
          </button>
        </div>
      </div>

      {/* Info Card */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 sm:p-4 dark:bg-yellow-900/30 dark:border-yellow-700">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-sm sm:text-base text-yellow-800 dark:text-yellow-300">Как определяются подозрительные транзакции?</h3>
            <ul className="text-xs sm:text-sm text-yellow-700 mt-2 space-y-1 dark:text-yellow-400">
              <li>• Сумма значительно выше обычной для категории</li>
              <li>• Необычное время совершения (ночь)</li>
              <li>• Крупная сумма транзакции</li>
              <li>• Нетипичный паттерн расходов</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Transactions List */}
      {transactions.length === 0 ? (
        <div className={`${cardClass} p-8 sm:p-12 text-center`}>
          <CheckCircle className="w-10 h-10 sm:w-12 sm:h-12 text-green-400 mx-auto mb-4" />
          <p className="text-sm sm:text-base text-gray-600 font-medium dark:text-gray-300">Всё в порядке!</p>
          <p className={`text-xs sm:text-sm ${mutedClass} mt-2`}>Подозрительных транзакций не обнаружено</p>
        </div>
      ) : (
        <div className="space-y-3 sm:space-y-4">
          {transactions.map((transaction) => (
            <div key={transaction.id} className={`${cardClass} border-l-4 border-red-500`}>
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="flex items-start gap-3 sm:gap-4 min-w-0">
                  <div className="p-2 sm:p-3 bg-red-100 rounded-lg dark:bg-red-900/30 shrink-0">
                    <AlertTriangle className="w-5 h-5 sm:w-6 sm:h-6 text-red-600 dark:text-red-400" />
                  </div>
                  <div className="min-w-0">
                    <h3 className={`font-semibold text-sm sm:text-base ${titleClass} truncate`}>{transaction.description || 'Без описания'}</h3>
                    <p className="text-xs sm:text-sm text-gray-500 mt-1 dark:text-gray-400">{getCategoryName(transaction.category_id)}</p>
                    <p className={`text-xs ${mutedClass} mt-1`}>{formatDate(transaction.transaction_date)}</p>
                    {transaction.suspicious_reason && (
                      <p className="text-xs sm:text-sm text-red-600 mt-2 flex items-center gap-1 dark:text-red-400">
                        <Eye className="w-3 h-3 sm:w-4 sm:h-4 shrink-0" />
                        <span className="break-words">{transaction.suspicious_reason}</span>
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2 sm:gap-3 shrink-0">
                  <p className="text-lg sm:text-xl font-bold text-red-600 dark:text-red-400">{formatCurrency(transaction.amount)}</p>
                  {reportedIds.has(transaction.id) ? (
                    <div className="p-2 sm:p-3 bg-red-50 rounded-lg border border-red-200 text-left w-full sm:max-w-xs dark:bg-red-900/30 dark:border-red-700">
                      <p className="text-xs sm:text-sm font-semibold text-red-700 mb-2 dark:text-red-400">⚠️ Рекомендации:</p>
                      <ul className="text-xs text-red-600 space-y-1 dark:text-red-400">
                        <li>1. Заблокируйте карту</li>
                        <li>2. Позвоните в банк</li>
                        <li>3. Напишите заявление</li>
                      </ul>
                      <button
                        onClick={() => openConfirmModal(transaction.id, 'remove')}
                        className="mt-2 sm:mt-3 w-full px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors text-xs dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                      >
                        Разобрался, убрать
                      </button>
                    </div>
                  ) : (
                    <div className="flex gap-2 w-full sm:w-auto">
                      <button
                        onClick={() => openConfirmModal(transaction.id, 'dismiss')}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-1 px-2 sm:px-3 py-1.5 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50"
                      >
                        <CheckCircle className="w-4 h-4" />
                        <span className="text-xs sm:text-sm">Всё в порядке</span>
                      </button>
                      <button
                        onClick={() => openConfirmModal(transaction.id, 'report')}
                        className="flex-1 sm:flex-none flex items-center justify-center gap-1 px-2 sm:px-3 py-1.5 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50"
                      >
                        <XCircle className="w-4 h-4" />
                        <span className="text-xs sm:text-sm">Подозрительная</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmModal
        isOpen={confirmModal.isOpen}
        onClose={closeConfirmModal}
        onConfirm={modalProps.onConfirm}
        title={modalProps.title}
        message={modalProps.message}
        confirmText={modalProps.confirmText}
        confirmColor={modalProps.confirmColor}
      />
    </div>
  );
}
