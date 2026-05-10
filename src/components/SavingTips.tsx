import { useState, useEffect } from 'react';
import { Lightbulb, TrendingDown, Sparkles } from 'lucide-react';
import { api, SavingTipsData } from '../api';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 0 }).format(value);
};

const PRIORITY_COLORS: Record<string, string> = {
  high: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

export default function SavingTips() {
  const [data, setData] = useState<SavingTipsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadTips = async () => {
      try {
        const tips = await api.getSavingTips();
        setData(tips);
      } catch (error) {
        console.error('Error loading tips:', error);
        setData(null);
      } finally {
        setIsLoading(false);
      }
    };
    loadTips();
  }, []);

  const cardClass = "bg-white rounded-xl shadow-sm p-6 dark:bg-gray-800";
  const titleClass = "text-gray-800 dark:text-white";
  const mutedClass = "text-gray-400 dark:text-gray-500";

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400"></div>
      </div>
    );
  }

  if (!data || data.tips.length === 0) {
    return (
      <div className={`${cardClass} p-12 text-center`}>
        <Lightbulb className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
        <p className={mutedClass}>Пока нет рекомендаций</p>
        <p className={`text-sm ${mutedClass} mt-2`}>Добавьте больше транзакций для анализа</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className={`text-2xl font-bold ${titleClass}`}>Советы по экономии</h2>
        <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
          <TrendingDown className="w-5 h-5" />
          <span className="font-semibold">Потенциальная экономия: {formatCurrency(data.total_potential_savings)}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {data.tips.map((tip) => (
          <div key={tip.id} className={cardClass}>
            <div className="flex items-start gap-4">
              <div className="p-3 bg-yellow-100 rounded-lg dark:bg-yellow-900/30">
                <Lightbulb className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className={`font-semibold ${titleClass}`}>{tip.title}</h3>
                  <span className={`px-2 py-0.5 text-xs rounded-full ${PRIORITY_COLORS[tip.priority] || PRIORITY_COLORS.low}`}>
                    {tip.priority === 'high' ? 'Важно' : tip.priority === 'medium' ? 'Средне' : 'Инфо'}
                  </span>
                </div>
                <p className="text-gray-500 text-sm dark:text-gray-400">{tip.description}</p>
                {tip.potential_savings && (
                  <div className="flex items-center gap-2 mt-3 text-green-600 dark:text-green-400">
                    <Sparkles className="w-4 h-4" />
                    <span className="text-sm font-medium">Экономия до {formatCurrency(tip.potential_savings)} в месяц</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}