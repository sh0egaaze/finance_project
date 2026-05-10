import { Plus, LogOut } from 'lucide-react';
import { User } from '../api';

interface HeaderProps {
  user: User | null;
  onLogout: () => void;
  onAddTransaction: () => void;
}

export default function Header({ user, onLogout, onAddTransaction }: HeaderProps) {
  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-[13px] sticky top-0 z-30 shrink-0">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
            {user?.full_name || 'Пользователь'}
          </h2>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            {new Date().toLocaleDateString('ru-RU', {
              weekday: 'long',
              year: 'numeric',
              month: 'long',
              day: 'numeric',
            })}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onAddTransaction}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors shadow-sm text-sm font-medium"
          >
            <Plus className="w-4 h-4" />
            Добавить
          </button>

          <div className="flex items-center gap-3 pl-3 border-l border-gray-200 dark:border-gray-700">
            <div className="hidden md:block">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{user?.full_name}</p>
              <p className="text-xs text-gray-400 dark:text-gray-500">{user?.email}</p>
            </div>
            <button
              onClick={onLogout}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors dark:hover:bg-red-900/20"
              title="Выйти"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}