import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { api, PredictionsData } from '../api';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 0 }).format(value);
};

// Единые стили для графиков
const chartStyles = {
  grid: { stroke: '#374151', strokeDasharray: '3 3', opacity: 0.2 },
  tick: { fill: '#9CA3AF', fontSize: 12 },
  tooltip: { backgroundColor: '#1F2937', border: 'none', borderRadius: '8px', color: '#F9FAFB' },
  itemStyle: { color: '#F9FAFB' },
};

export default function Predictions() {
  const [data, setData] = useState<PredictionsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadPredictions = async () => {
      try {
        const predictions = await api.getPredictions();
        setData(predictions);
      } catch (err) {
        console.error('Error loading predictions:', err);
        setError('Не удалось загрузить прогнозы');
        setData(null);
      } finally {
        setIsLoading(false);
      }
    };
    loadPredictions();
  }, []);

  const cardClass = "bg-white rounded-xl shadow-sm border border-gray-100 p-6 dark:bg-gray-800 dark:border-gray-700";
  const titleClass = "text-gray-800 dark:text-white";
  const subtitleClass = "text-gray-500 text-sm dark:text-gray-400";
  const mutedClass = "text-gray-400 dark:text-gray-500";

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className={`${cardClass} p-12 text-center`}>
        <AlertCircle className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
        <p className={mutedClass}>Недостаточно данных для прогнозов</p>
        <p className={`text-sm ${mutedClass} mt-2`}>Добавьте больше транзакций</p>
      </div>
    );
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return <TrendingUp className="w-4 h-4 text-red-500" />;
      case 'down': return <TrendingDown className="w-4 h-4 text-green-500" />;
      default: return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  const predictions = data.by_category || [];

  return (
    <div className="space-y-6">
      <h2 className={`text-2xl font-bold ${titleClass}`}>Прогнозы</h2>

      {error && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 p-4 rounded-lg dark:bg-yellow-900/30 dark:border-yellow-700 dark:text-yellow-400">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className={cardClass}>
          <p className={subtitleClass}>Ожидаемые доходы</p>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">{formatCurrency(data.next_month_income)}</p>
          <p className={`text-sm ${mutedClass} mt-2`}>на следующий месяц</p>
        </div>
        <div className={cardClass}>
          <p className={subtitleClass}>Ожидаемые расходы</p>
          <p className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">{formatCurrency(data.next_month_expense)}</p>
          <p className={`text-sm ${mutedClass} mt-2`}>на следующий месяц</p>
        </div>
        <div className={cardClass}>
          <p className={subtitleClass}>Ожидаемый баланс</p>
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">{formatCurrency(data.next_month_income - data.next_month_expense)}</p>
          <p className={`text-sm ${mutedClass} mt-2`}>накопления</p>
        </div>
      </div>

      {/* Predictions by Category */}
      {predictions.length > 0 && (
        <div className={cardClass}>
          <h3 className={`text-lg font-semibold ${titleClass} mb-4`}>Прогноз по категориям</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={predictions}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
              <XAxis dataKey="name" tick={chartStyles.tick} />
              <YAxis tickFormatter={(v) => Number(v).toLocaleString('ru-RU')} width={70} tick={chartStyles.tick} />
              <Tooltip formatter={(value) => [formatCurrency(Number(value)), 'Сумма']} contentStyle={chartStyles.tooltip} itemStyle={chartStyles.itemStyle} labelStyle={chartStyles.itemStyle} />
              <Bar dataKey="predicted_amount" radius={[4, 4, 0, 0]}>
                {predictions.map((entry, index) => (
                  <Cell key={index} fill={entry.color || '#3B82F6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          <div className="mt-6 space-y-3">
            {predictions.map((pred) => (
              <div key={pred.category_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg dark:bg-gray-700">
                <div className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: pred.color || '#6B7280' }} />
                  <span className="text-gray-700 dark:text-gray-300">{pred.name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className={`font-semibold ${titleClass}`}>{formatCurrency(pred.predicted_amount)}</span>
                  {getTrendIcon(pred.trend)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {predictions.length === 0 && (
        <div className={`${cardClass} p-12 text-center`}>
          <AlertCircle className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
          <p className={mutedClass}>Недостаточно данных для прогнозов по категориям</p>
          <p className={`text-sm ${mutedClass} mt-2`}>Добавьте больше транзакций за разные периоды</p>
        </div>
      )}
    </div>
  );
}