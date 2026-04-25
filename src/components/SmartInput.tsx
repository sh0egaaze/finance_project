import React, { useState, useCallback } from 'react';
import { Send, Loader2, Check, AlertCircle } from 'lucide-react';
import { api, SmartInputResult } from '../api';

interface SmartInputProps {
  onTransactionAdded: () => void;
}

export const SmartInput: React.FC<SmartInputProps> = ({ onTransactionAdded }) => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<SmartInputResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Превью при вводе
  const handleInputChange = useCallback(async (value: string) => {
    setText(value);
    setError(null);
    setSuccess(false);
    
    if (value.length < 3) {
      setPreview(null);
      return;
    }

    try {
      const result = await api.smartInput(value);
      setPreview(result);
    } catch {
      setPreview(null);
    }
  }, []);

  // Отправка
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!text.trim() || loading) return;

    setLoading(true);
    setError(null);

    try {
      await api.smartInputConfirm(text);
      setSuccess(true);
      setText('');
      setPreview(null);
      onTransactionAdded();
      
      // Сбрасываем успех через 2 сек
      setTimeout(() => setSuccess(false), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Не удалось добавить транзакцию');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-2">
        Быстрый ввод
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        Просто напишите, например: "кофе 250" или "зарплата 85000"
      </p>
      
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <input
            type="text"
            value={text}
            onChange={(e) => handleInputChange(e.target.value)}
            placeholder="кола 100"
            className={`w-full pl-4 pr-12 py-4 text-lg border-2 rounded-xl transition-colors ${
              success 
                ? 'border-green-500 bg-green-50' 
                : error 
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-200 focus:border-blue-500'
            } focus:outline-none`}
            disabled={loading}
          />
          
          <button
            type="submit"
            disabled={loading || !text.trim()}
            className={`absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg transition-all ${
              loading || !text.trim()
                ? 'bg-gray-100 text-gray-400'
                : success
                  ? 'bg-green-500 text-white'
                  : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : success ? (
              <Check className="w-5 h-5" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Превью */}
        {preview && !success && (
          <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-gray-600">{preview.description}</span>
                {preview.category_name && (
                  <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                    {preview.category_name}
                  </span>
                )}
              </div>
              {preview.amount && (
                <span className={`font-semibold ${preview.is_income ? 'text-green-600' : 'text-red-600'}`}>
                  {preview.is_income ? '+' : '-'}{Math.abs(preview.amount).toLocaleString('ru-RU')} ₽
                </span>
              )}
            </div>
            {preview.category_confidence && preview.category_confidence > 0 && (
              <div className="mt-2 flex items-center gap-2">
                <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-blue-500 rounded-full"
                    style={{ width: `${preview.category_confidence * 100}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500">
                  {Math.round(preview.category_confidence * 100)}% уверенность
                </span>
              </div>
            )}
          </div>
        )}

        {/* Ошибка */}
        {error && (
          <div className="mt-3 p-3 bg-red-50 rounded-lg border border-red-200 flex items-center gap-2 text-red-700">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* Успех */}
        {success && (
          <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-200 flex items-center gap-2 text-green-700">
            <Check className="w-4 h-4" />
            <span className="text-sm">Транзакция добавлена!</span>
          </div>
        )}
      </form>

      {/* Подсказки */}
      <div className="mt-4 flex flex-wrap gap-2">
        {['кофе 200', 'такси 450', 'зарплата 85000', 'netflix 999'].map((hint) => (
          <button
            key={hint}
            onClick={() => handleInputChange(hint)}
            className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-full transition-colors"
          >
            {hint}
          </button>
        ))}
      </div>
    </div>
  );
};
