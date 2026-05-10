import { useState, useEffect } from 'react';
import { ArrowRight } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line,
} from 'recharts';
import { api, AnalyticsData } from '../api';

const formatCurrency = (value: number) => {
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 0 }).format(value);
};

const chartStyles = {
  grid: { stroke: '#374151', strokeDasharray: '3 3', opacity: 0.2 },
  tick: { fill: '#9CA3AF', fontSize: 12 },
  tooltip: { backgroundColor: '#1F2937', border: 'none', borderRadius: '8px', color: '#F9FAFB' },
  itemStyle: { color: '#F9FAFB' },
};

const shortenName = (name: string, maxLen: number = 16) => {
  return name.length > maxLen ? name.substring(0, maxLen) + '…' : name;
};

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showIncome, setShowIncome] = useState(false);

  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  const firstDayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`;
  const [dateFrom, setDateFrom] = useState(firstDayStr);
  const [dateTo, setDateTo] = useState(todayStr);

  useEffect(() => {
    const loadAnalytics = async () => {
      setIsLoading(true);
      try {
        const analytics = await api.getAnalytics(undefined, dateFrom, dateTo);
        setData(analytics);
      } catch (error) {
        console.error('Error loading analytics:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadAnalytics();
  }, [dateFrom, dateTo]);

  const cardClass = "bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 p-6";
  const inputClass = "px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm bg-white dark:bg-gray-700 dark:text-white";
  const switchBtn = "p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors";
  const titleClass = "text-lg font-semibold text-gray-800 dark:text-white";

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
        <p className="text-gray-400 dark:text-gray-500">Не удалось загрузить аналитику</p>
      </div>
    );
  }

  const spendingByCategory = (data.spending_by_category || []).map(item => ({
    ...item,
    fill: item.color || '#6B7280',
  }));
  const incomeByCategory = (data.income_by_category || []).map((item: any) => ({
    ...item,
    fill: item.color || '#22c55e',
  }));
  const totalSpending = spendingByCategory.reduce((a, b) => a + b.amount, 0);
  const totalIncomeCalc = incomeByCategory.reduce((a: number, b: any) => a + b.amount, 0);

  const currentChartData = showIncome ? incomeByCategory : spendingByCategory;
  const currentTotal = showIncome ? totalIncomeCalc : totalSpending;

  if (spendingByCategory.length === 0 && incomeByCategory.length === 0) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-white">Аналитика</h2>
        <div className={`${cardClass} p-12 text-center`}>
          <p className="text-gray-400 dark:text-gray-500">Недостаточно данных для аналитики</p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-2">Добавьте транзакции, чтобы увидеть статистику</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800 dark:text-white">Аналитика</h2>
        <div className="flex items-center gap-2">
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className={inputClass} />
          <span className="text-gray-400">—</span>
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className={inputClass} />
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className={cardClass}>
          <p className="text-gray-500 dark:text-gray-400 text-sm">Доходы</p>
          <p className="text-2xl font-bold text-green-600 dark:text-green-400">{formatCurrency(data.total_income || 0)}</p>
        </div>
        <div className={cardClass}>
          <p className="text-gray-500 dark:text-gray-400 text-sm">Расходы</p>
          <p className="text-2xl font-bold text-red-600 dark:text-red-400">{formatCurrency(totalSpending)}</p>
        </div>
        <div className={cardClass}>
          <p className="text-gray-500 dark:text-gray-400 text-sm">Баланс</p>
          <p className={`text-2xl font-bold ${(data.total_income || 0) - totalSpending >= 0 ? 'text-blue-600 dark:text-blue-400' : 'text-red-600 dark:text-red-400'}`}>
            {formatCurrency((data.total_income || 0) - totalSpending)}
          </p>
        </div>
        <div className={cardClass}>
          <p className="text-gray-500 dark:text-gray-400 text-sm">Топ категория</p>
          <p className="text-2xl font-bold text-gray-800 dark:text-white">
            {spendingByCategory.length > 0 ? [...spendingByCategory].sort((a, b) => b.amount - a.amount)[0].name : '-'}
          </p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bar Chart */}
        <div className={cardClass}>
          <div className="flex items-center justify-between mb-4">
            <h3 className={titleClass}>{showIncome ? 'Доходы по категориям' : 'Расходы по категориям'}</h3>
            <button onClick={() => setShowIncome(!showIncome)} className={switchBtn} title={showIncome ? 'Показать расходы' : 'Показать доходы'}>
              <ArrowRight className="w-5 h-5 text-gray-400 hover:text-blue-500" />
            </button>
          </div>
          {currentChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={currentChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
                <XAxis
                  dataKey="name"
                  tick={chartStyles.tick}
                  tickFormatter={(name) => shortenName(name)}
                  interval={0}
                />
                <YAxis tickFormatter={(v) => Number(v).toLocaleString('ru-RU')} width={70} tick={chartStyles.tick} />
                <Tooltip formatter={(value) => [formatCurrency(Number(value)), 'Сумма']} contentStyle={chartStyles.tooltip} itemStyle={chartStyles.itemStyle} labelStyle={chartStyles.itemStyle} />
                <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                  {currentChartData.map((entry: any, index: number) => (
                    <Cell key={index} fill={entry.fill || entry.color || (showIncome ? '#22c55e' : '#6B7280')} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-400 dark:text-gray-500">
              {showIncome ? 'Нет доходов' : 'Нет расходов'}
            </div>
          )}
        </div>

        {/* Pie Chart with Legend */}
        <div className={cardClass}>
          <div className="flex items-center justify-between mb-4">
            <h3 className={titleClass}>{showIncome ? 'Структура доходов' : 'Структура расходов'}</h3>
            <button onClick={() => setShowIncome(!showIncome)} className={switchBtn} title={showIncome ? 'Показать расходы' : 'Показать доходы'}>
              <ArrowRight className="w-5 h-5 text-gray-400 hover:text-blue-500" />
            </button>
          </div>
          {currentChartData.length > 0 ? (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="50%" height={250}>
                <PieChart>
                  <Pie
                    data={currentChartData}
                    dataKey="amount"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                  >
                    {currentChartData.map((entry: any, index: number) => (
                      <Cell key={index} fill={entry.fill || entry.color || (showIncome ? '#22c55e' : '#6B7280')} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [formatCurrency(Number(value))]} contentStyle={chartStyles.tooltip} itemStyle={chartStyles.itemStyle} labelStyle={chartStyles.itemStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2 max-h-[250px] overflow-y-auto">
                {currentChartData.map((cat: any) => {
                  const percentage = currentTotal > 0 ? (cat.amount / currentTotal) * 100 : 0;
                  return (
                    <div key={cat.category_id || cat.name} className="flex items-center justify-between">
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: cat.fill || cat.color || (showIncome ? '#22c55e' : '#6B7280') }} />
                        <span className="text-sm text-gray-600 dark:text-gray-300 truncate">{cat.name}</span>
                      </div>
                      <span className="text-sm font-medium text-gray-500 dark:text-gray-400 ml-2 shrink-0">{percentage.toFixed(1)}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-gray-400 dark:text-gray-500">
              {showIncome ? 'Нет доходов' : 'Нет расходов'}
            </div>
          )}
        </div>
      </div>

      {/* Trend */}
      {data.spending_trend && data.spending_trend.length > 0 && (
        <div className={cardClass}>
          <h3 className={`${titleClass} mb-4`}>Динамика доходов и расходов</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data.spending_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.2} />
              <XAxis dataKey="date" tick={chartStyles.tick} />
              <YAxis tickFormatter={(v) => Number(v).toLocaleString('ru-RU')} width={70} tick={chartStyles.tick} />
              <Tooltip
                formatter={(value, name) => [formatCurrency(Number(value)), name === 'income' ? 'Доходы' : 'Расходы']}
                contentStyle={chartStyles.tooltip}
                itemStyle={chartStyles.itemStyle}
                labelStyle={chartStyles.itemStyle}
              />
              <Line type="monotone" dataKey="income" stroke="#10B981" name="Доходы" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              <Line type="monotone" dataKey="expense" stroke="#EF4444" name="Расходы" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Details */}
      <div className={cardClass}>
        <div className="flex items-center justify-between mb-4">
          <h3 className={titleClass}>{showIncome ? 'Детали по доходам' : 'Детали по расходам'}</h3>
          <button onClick={() => setShowIncome(!showIncome)} className={switchBtn} title={showIncome ? 'Показать расходы' : 'Показать доходы'}>
            <ArrowRight className="w-5 h-5 text-gray-400 hover:text-blue-500" />
          </button>
        </div>
        {currentChartData.length > 0 ? (
          <div className="space-y-3">
            {[...currentChartData].sort((a: any, b: any) => b.amount - a.amount).map((item: any) => {
              const percentage = currentTotal > 0 ? (item.amount / currentTotal) * 100 : 0;
              return (
                <div key={item.category_id || item.name} className="flex items-center gap-4">
                  <div className="w-4 h-4 rounded-full shrink-0" style={{ backgroundColor: item.fill || item.color || (showIncome ? '#22c55e' : '#6B7280') }} />
                  <span className="flex-1 text-gray-700 dark:text-gray-300">{item.name}</span>
                  <span className="text-gray-500 dark:text-gray-400">{percentage.toFixed(1)}%</span>
                  <span className="font-semibold text-gray-800 dark:text-white w-28 text-right">{formatCurrency(item.amount)}</span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="py-8 text-center text-gray-400 dark:text-gray-500">
            {showIncome ? 'Нет доходов за выбранный период' : 'Нет расходов за выбранный период'}
          </div>
        )}
      </div>
    </div>
  );
}