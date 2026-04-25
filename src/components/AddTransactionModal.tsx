import { useState, useEffect } from 'react';
import { X, Sparkles } from 'lucide-react';
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

const CATEGORY_KEYWORDS: Record<string, string[]> = {
  FOOD: ['еда', 'кофе', 'обед', 'ужин', 'завтрак', 'ресторан', 'кафе', 'продукты', 'магазин', 'пятёрочка', 'магнит', 'перекрёсток', 'булочка', 'пицца', 'суши', 'кола', 'бургер'],
  TRANSPORT: ['такси', 'метро', 'автобус', 'бензин', 'заправка', 'транспорт', 'яндекс драйв', 'uber', 'bolt'],
  ENTERTAINMENT: ['кино', 'театр', 'концерт', 'развлечения', 'игры', 'netflix', 'spotify', 'подписка'],
  SHOPPING: ['одежда', 'обувь', 'покупки', 'wildberries', 'ozon', 'aliexpress', 'zara', 'hm'],
  UTILITIES: ['жкх', 'коммунальные', 'квартплата', 'интернет', 'электричество', 'газ', 'вода'],
  HEALTH: ['аптека', 'лекарства', 'врач', 'больница', 'анализы', 'стоматолог'],
  EDUCATION: ['курсы', 'обучение', 'книги', 'школа', 'университет'],
  TRAVEL: ['отель', 'билеты', 'путешествие', 'отдых', 'самолёт', 'поезд'],
  INCOME: ['зарплата', 'перевод', 'доход', 'фриланс', 'премия'],
  SALARY: ['зарплата', 'аванс', 'оклад'],
};

function categorizeDescription(description: string, categories: Category[]): { category: Category | null; confidence: number } {
  const lowerDesc = description.toLowerCase();
  
  for (const [code, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    for (const keyword of keywords) {
      if (lowerDesc.includes(keyword)) {
        const cat = categories.find(c => c.code === code);
        return { category: cat || null, confidence: 0.85 };
      }
    }
  }
  
  const otherCat = categories.find(c => c.code === 'OTHER');
  return { category: otherCat || null, confidence: 0.5 };
}

export default function AddTransactionModal({ categories, onSubmit, onClose }: AddTransactionModalProps) {
  const [description, setDescription] = useState('');
  const [amount, setAmount] = useState('');
  const [categoryId, setCategoryId] = useState<number | null>(null);
  const [type, setType] = useState<'income' | 'expense'>('expense');
  const [source, setSource] = useState<string>('manual');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState<{ category: Category | null; confidence: number } | null>(null);

  // Auto-categorize when description changes
  useEffect(() => {
    if (description.length > 2 && categories.length > 0) {
      const suggestion = categorizeDescription(description, categories);
      setAiSuggestion(suggestion);
      if (!categoryId && suggestion.category) {
        setCategoryId(suggestion.category.id);
      }
    } else {
      setAiSuggestion(null);
    }
  }, [description, categories]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description || !amount) return;

    setIsSubmitting(true);
    try {
      await onSubmit({
        amount: Number(amount),
        description,
        category_id: categoryId,
        type,
        source,
        date,
      });
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

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-semibold text-gray-800">Добавить транзакцию</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="w-6 h-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Type Toggle */}
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              type="button"
              onClick={() => setType('expense')}
              className={`flex-1 py-2 rounded-md transition-colors ${
                type === 'expense' ? 'bg-red-500 text-white' : 'text-gray-600'
              }`}
            >
              Расход
            </button>
            <button
              type="button"
              onClick={() => setType('income')}
              className={`flex-1 py-2 rounded-md transition-colors ${
                type === 'income' ? 'bg-green-500 text-white' : 'text-gray-600'
              }`}
            >
              Доход
            </button>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Описание *
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Например: Кофе в Старбакс"
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              required
            />
            {aiSuggestion && aiSuggestion.category && (
              <div className="flex items-center gap-2 mt-2 text-sm text-blue-600">
                <Sparkles className="w-4 h-4" />
                <span>
                  ИИ определил категорию: {aiSuggestion.category.icon} {aiSuggestion.category.name}
                  ({Math.round(aiSuggestion.confidence * 100)}%)
                </span>
              </div>
            )}
          </div>

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Сумма *
            </label>
            <div className="relative">
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0"
                min="0"
                step="0.01"
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 pr-12"
                required
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400">₽</span>
            </div>
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Категория
            </label>
            <select
              value={categoryId || ''}
              onChange={(e) => setCategoryId(e.target.value ? Number(e.target.value) : null)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Автоопределение</option>
              {displayCategories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.icon} {cat.name}
                </option>
              ))}
            </select>
          </div>

          {/* Source */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Источник
            </label>
            <div className="flex gap-3">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="source"
                  value="manual"
                  checked={source === 'manual'}
                  onChange={() => setSource('manual')}
                  className="text-blue-600"
                />
                <span>Вручную</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="source"
                  value="tbank_api"
                  checked={source === 'tbank_api'}
                  onChange={() => setSource('tbank_api')}
                  className="text-blue-600"
                />
                <span>Т-Банк</span>
              </label>
            </div>
          </div>

          {/* Date */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Дата
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border rounded-lg hover:bg-gray-50 transition-colors"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !description || !amount}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isSubmitting ? 'Добавление...' : 'Добавить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
