import React, { useState } from 'react';
import { Send, Loader2, Check, AlertCircle } from 'lucide-react';
import { api } from '../api';

interface SmartInputProps {
  onTransactionAdded: () => void;
}

export const SmartInput: React.FC<SmartInputProps> = ({ onTransactionAdded }) => {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!text.trim() || loading) return;

    setLoading(true);
    setError(null);

    try {
      await api.smartInputConfirm(text);
      setSuccess(true);
      setText('');
      onTransactionAdded();
      
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
        Просто напишите, например: &quot;кофе 250&quot; или &quot;зарплата 85000&quot;
      </p>
      
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <input
            type="text"
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              setError(null);
              setSuccess(false);
            }}
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

        {error && (
          <div className="mt-3 p-3 bg-red-50 rounded-lg border border-red-200 flex items-center gap-2 text-red-700">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {success && (
          <div className="mt-3 p-3 bg-green-50 rounded-lg border border-green-200 flex items-center gap-2 text-green-700">
            <Check className="w-4 h-4" />
            Транзакция добавлена!
          </div>
        )}
      </form>
    </div>
  );
};