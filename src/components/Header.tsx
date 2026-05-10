import { Plus, LogOut, User as UserIcon } from 'lucide-react';
import { User } from '../api';

interface HeaderProps {
  user: User | null;
  onLogout: () => void;
  onAddTransaction: () => void;
}

export default function Header({ user, onLogout, onAddTransaction }: HeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 sticky top-0 z-30 shrink-0">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">
            {user?.full_name || 'Пользователь'}
          </h2>
          <p className="text-xs text-gray-400">
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

          <div className="flex items-center gap-3 pl-3 border-l border-gray-200">
            <div className="w-9 h-9 bg-gradient-to-br from-blue-400 to-indigo-500 rounded-full flex items-center justify-center shadow-sm">
              <UserIcon className="w-4 h-4 text-white" />
            </div>
            <div className="hidden md:block">
              <p className="text-sm font-medium text-gray-700">{user?.full_name}</p>
              <p className="text-xs text-gray-400">{user?.email}</p>
            </div>
            <button
              onClick={onLogout}
              className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
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