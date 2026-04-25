import { useState, useEffect } from 'react';
import { RefreshCw, TrendingUp, TrendingDown, ArrowRightLeft } from 'lucide-react';
import { api, CurrencyRatesData } from '../api';

export default function CurrencyRates() {
  const [data, setData] = useState<CurrencyRatesData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Converter state
  const [amount, setAmount] = useState<string>('1000');
  const [fromCurrency, setFromCurrency] = useState('RUB');
  const [toCurrency, setToCurrency] = useState('USD');
  const [convertedAmount, setConvertedAmount] = useState<number | null>(null);

  const loadRates = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const rates = await api.getCurrencyRates();
      setData(rates);
    } catch (err) {
      console.error('Error loading currency rates:', err);
      // Use fallback data
      setData({
        base: 'RUB',
        date: new Date().toISOString(),
        rates: [
          { currency: 'USD', rate: 92.50, change: 0.25, name: 'Доллар США', flag: '🇺🇸' },
          { currency: 'EUR', rate: 100.20, change: -0.15, name: 'Евро', flag: '🇪🇺' },
          { currency: 'CNY', rate: 12.80, change: 0.10, name: 'Юань', flag: '🇨🇳' },
          { currency: 'GBP', rate: 117.30, change: 0.45, name: 'Фунт', flag: '🇬🇧' },
        ],
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRates();
  }, []);

  const handleConvert = async () => {
    if (!amount || !data) return;
    
    try {
      const result = await api.convertCurrency(Number(amount), fromCurrency, toCurrency);
      setConvertedAmount(result.result);
    } catch {
      // Calculate locally
      const fromRate = fromCurrency === 'RUB' ? 1 : (data.rates.find(r => r.currency === fromCurrency)?.rate || 1);
      const toRate = toCurrency === 'RUB' ? 1 : (data.rates.find(r => r.currency === toCurrency)?.rate || 1);
      const result = Number(amount) * fromRate / toRate;
      setConvertedAmount(result);
    }
  };

  const swapCurrencies = () => {
    setFromCurrency(toCurrency);
    setToCurrency(fromCurrency);
    setConvertedAmount(null);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 text-red-600 p-4 rounded-lg">
        {error}
        <button onClick={loadRates} className="ml-4 underline">
          Попробовать снова
        </button>
      </div>
    );
  }

  const rates = data?.rates || [];
  const currencies = ['RUB', ...rates.map(r => r.currency)];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-800">Курсы валют</h2>
        <button
          onClick={loadRates}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Обновить
        </button>
      </div>

      {/* Currency Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {rates.map((rate) => (
          <div key={rate.currency} className="bg-white rounded-xl shadow-sm p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-2xl">{rate.flag}</span>
              <span className={`flex items-center gap-1 text-sm ${
                rate.change >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {rate.change >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                {rate.change >= 0 ? '+' : ''}{rate.change.toFixed(2)}%
              </span>
            </div>
            <div className="text-sm text-gray-500">{rate.name}</div>
            <div className="text-2xl font-bold text-gray-800 mt-1">
              {rate.rate.toFixed(2)} ₽
            </div>
            <div className="text-sm text-gray-400">1 {rate.currency}</div>
          </div>
        ))}
      </div>

      {/* Converter */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">Конвертер валют</h3>
        
        <div className="flex flex-col md:flex-row items-center gap-4">
          <div className="flex-1 w-full">
            <label className="block text-sm text-gray-500 mb-1">У меня есть</label>
            <div className="flex gap-2">
              <input
                type="number"
                value={amount}
                onChange={(e) => {
                  setAmount(e.target.value);
                  setConvertedAmount(null);
                }}
                className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                placeholder="Сумма"
              />
              <select
                value={fromCurrency}
                onChange={(e) => {
                  setFromCurrency(e.target.value);
                  setConvertedAmount(null);
                }}
                className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                {currencies.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            onClick={swapCurrencies}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <ArrowRightLeft className="w-6 h-6 text-gray-400" />
          </button>

          <div className="flex-1 w-full">
            <label className="block text-sm text-gray-500 mb-1">Получу</label>
            <div className="flex gap-2">
              <input
                type="text"
                value={convertedAmount !== null ? convertedAmount.toFixed(2) : ''}
                readOnly
                className="flex-1 px-4 py-2 border rounded-lg bg-gray-50"
                placeholder="Результат"
              />
              <select
                value={toCurrency}
                onChange={(e) => {
                  setToCurrency(e.target.value);
                  setConvertedAmount(null);
                }}
                className="px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                {currencies.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          <button
            onClick={handleConvert}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap"
          >
            Конвертировать
          </button>
        </div>
      </div>

      {/* Last Update */}
      {data && (
        <p className="text-sm text-gray-400 text-center">
          Обновлено: {new Date(data.date).toLocaleString('ru-RU')}
        </p>
      )}
    </div>
  );
}
