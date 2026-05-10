import { useState } from 'react';
import { X } from 'lucide-react';
import { Category } from '../api';

interface AddTransactionModalProps {
  categories: Category[];
  onSubmit: (data: {
    amount: number;
    description: string;
    category_id: number | null;
    type: 'income' | 'expense';
    source: string;
    date: string;
  }) => Promise<void>;
  onClose: () => void;
}

export default function AddTransactionModal({ categories, onSubmit, onClose }: AddTransactionModalProps) {
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [type, setType] = useState<'income' | 'expense'>('expense');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [time, setTime] = useState(
      new Date().toLocaleTimeString('sv-SE', { hour: '2-digit', minute: '2-digit' })
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description || !amount) return;
    setIsSubmitting(true);
    try {
      await onSubmit({ amount: Number(amount), description, category_id: categoryId, type, source: 'manual', date: `${date}T${time}` });
      onClose();
    } catch (error) {
      console.error('Error creating transaction:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const expenseCategories = categories.filter(c => c.is_expense);
  const incomeCategories = categories.filter(c => c.is_income);
  const displayCategories = type === 'income' ? incomeCategories : expenseCategories;

  const inputClass = "w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400";
  const labelClass = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1";

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-semibold text-gray-800 dark:text-white">Добавить транзакцию</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
            <button type="button" onClick={() => { setType('expense'); setCategoryId(null); }}
              className={`flex-1 py-2 rounded-md transition-colors ${type === 'expense' ? 'bg-red-500 text-white' : 'text-gray-600 dark:text-gray-300'}`}>
              Расход
            </button>
            <button type="button" onClick={() => { setType('income'); setCategoryId(null); }}
              className={`flex-1 py-2 rounded-md transition-colors ${type === 'income' ? 'bg-green-500 text-white' : 'text-gray-600 dark:text-gray-300'}`}>
              Доход
            </button>
          </div>

          <div>
            <label className={labelClass}>Описание *</label>
            <input type="text" value={description} onChange={(e) => setDescription(e.target.value)}
              placeholder="Например: Кофе" className={inputClass} required />
          </div>

          <div>
            <label className={labelClass}>Сумма *</label>
            <div className="relative">
              <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)}
                placeholder="0" min="0" step="0.01" className={`${inputClass} pr-12`} required />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400">₽</span>
            </div>
          </div>

          <div>
            <label className={labelClass}>Категория *</label>
            <select value={categoryId || ''} onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : null)}
              className={inputClass} required>
              <option value="">Выберите категорию</option>
              {displayCategories.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.icon} {cat.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Дата</label>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>Время</label>
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className={inputClass} />
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button type="button" onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-700 dark:text-gray-300">
              Отмена
            </button>
            <button type="submit" disabled={isSubmitting || !description || !amount || !categoryId}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
              {isSubmitting ? 'Добавление...' : 'Добавить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}