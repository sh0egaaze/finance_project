import React, { useState, useEffect } from 'react';
import { X, Save, Loader2 } from 'lucide-react';
import { api, Transaction, Category } from '../api';

interface EditTransactionModalProps {
  transaction: Transaction;
  onClose: () => void;
  onSaved: () => void;
}

export const EditTransactionModal: React.FC<EditTransactionModalProps> = ({ transaction, onClose, onSaved }) => {
  const [description, setDescription] = useState(transaction.description || '');
  const [amount, setAmount] = useState(Math.abs(Number(transaction.amount)).toString());
  const [isExpense, setIsExpense] = useState(!transaction.is_income);
  const [categoryId, setCategoryId] = useState<number | null>(transaction.category_id);
  const [date, setDate] = useState(transaction.transaction_date ? new Date(transaction.transaction_date).toLocaleDateString('en-CA') : new Date().toLocaleDateString('en-CA'));
  const [time, setTime] = useState(transaction.transaction_date ? new Date(transaction.transaction_date).toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' }) : '12:00');
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const cats = await api.getCategories();
      setCategories(cats);
    } catch {
      console.error('Failed to load categories');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const amountValue = parseFloat(amount);
      if (isNaN(amountValue) || amountValue <= 0) {
        throw new Error('Введите корректную сумму');
      }
      await api.updateTransaction(transaction.id, {
        description,
        amount: amountValue,
        is_income: !isExpense,
        category_id: categoryId || undefined,
        transaction_date: new Date(`${date}T${time}`).toISOString(),
      });
      onSaved();
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Не удалось сохранить изменения');
      }
    } finally {
      setLoading(false);
    }
  };

  const labelClass = "block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300";
  const inputClass = "w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400 text-sm sm:text-base";

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto overflow-x-hidden dark:bg-gray-800">
        <div className="sticky top-0 bg-white dark:bg-gray-800 flex items-center justify-between p-4 border-b dark:border-gray-700">
          <h2 className="text-lg font-semibold dark:text-white">Редактирование транзакции</h2>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition-colors dark:hover:bg-gray-700">
            <X className="w-5 h-5 dark:text-gray-400" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Описание */}
          <div>
            <label className={labelClass}>Описание</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className={inputClass}
              placeholder="Описание транзакции"
            />
          </div>

          {/* Сумма и тип */}
          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <div>
              <label className={labelClass}>Сумма</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className={inputClass}
                placeholder="0"
                min="0"
                step="0.01"
              />
            </div>
            <div>
              <label className={labelClass}>Тип</label>
              <select
                value={isExpense ? 'expense' : 'income'}
                onChange={(e) => setIsExpense(e.target.value === 'expense')}
                className={inputClass}
              >
                <option value="expense">Расход</option>
                <option value="income">Доход</option>
              </select>
            </div>
          </div>

          {/* Категория */}
          <div>
            <label className={labelClass}>Категория</label>
            <select
              value={categoryId || ''}
              onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : null)}
              className={inputClass}
            >
              <option value="">Без категории</option>
              {categories
                .filter((c) => (isExpense ? c.is_expense : c.is_income))
                .map((cat) => (
                  <option key={cat.id} value={cat.id}>{cat.icon} {cat.name}</option>
                ))}
            </select>
          </div>

          {/* Дата и время */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Дата</label>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Время</label>
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className={inputClass} />
            </div>
          </div>

          {/* Ошибка */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm dark:bg-red-900/30 dark:border-red-700 dark:text-red-400">
              {error}
            </div>
          )}

          {/* Кнопки */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-2.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              Сохранить
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
