import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Minus, AlertCircle } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { api, PredictionsData } from '../api';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
  }).format(value);
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-12 text-center">
        <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-400">Недостаточно данных для прогнозов</p>
        <p className="text-sm text-gray-400 mt-2">Добавьте больше транзакций</p>
      </div>
    );
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp className="w-4 h-4 text-red-500" />;
      case 'down':
        return <TrendingDown className="w-4 h-4 text-green-500" />;
      default:
        return <Minus className="w-4 h-4 text-gray-400" />;
    }
  };

  const predictions = data.by_category || [];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">Прогнозы</h2>

      {error && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 p-4 rounded-lg">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm">Ожидаемые доходы</p>
          <p className="text-2xl font-bold text-green-600 mt-1">
            {formatCurrency(data.next_month_income)}
          </p>
          <p className="text-sm text-gray-400 mt-2">на следующий месяц</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm">Ожидаемые расходы</p>
          <p className="text-2xl font-bold text-red-600 mt-1">
            {formatCurrency(data.next_month_expense)}
          </p>
          <p className="text-sm text-gray-400 mt-2">на следующий месяц</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <p className="text-gray-500 text-sm">Ожидаемый баланс</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">
            {formatCurrency(data.next_month_income - data.next_month_expense)}
          </p>
          <p className="text-sm text-gray-400 mt-2">накопления</p>
        </div>
      </div>

      {/* Predictions by Category */}
      {predictions.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">Прогноз по категориям</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={predictions}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(value) => formatCurrency(Number(value))} />
              <Bar dataKey="predicted_amount" fill="#3B82F6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>

          <div className="mt-6 space-y-3">
            {predictions.map((pred) => (
              <div key={pred.category_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: pred.color || '#6B7280' }} 
                  />
                  <span className="text-gray-700">{pred.name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="font-semibold text-gray-800">
                    {formatCurrency(pred.predicted_amount)}
                  </span>
                  {getTrendIcon(pred.trend)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {predictions.length === 0 && (
        <div className="bg-white rounded-xl shadow-sm p-12 text-center">
          <AlertCircle className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-400">Недостаточно данных для прогнозов по категориям</p>
          <p className="text-sm text-gray-400 mt-2">Добавьте больше транзакций за разные периоды</p>
        </div>
      )}
    </div>
  );
}
