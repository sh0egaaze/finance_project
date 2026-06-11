import { useState } from 'react';
import { Wallet, Mail, Lock, User, Eye, EyeOff, CheckSquare, Square, X } from 'lucide-react';

interface AuthPageProps {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (email: string, password: string, fullName: string) => Promise<void>;
}

export default function AuthPage({ onLogin, onRegister }: AuthPageProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [showPrivacyPolicy, setShowPrivacyPolicy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    if (!isLogin && !agreedToTerms) {
      setError('Необходимо согласиться на обработку персональных данных');
      return;
    }
    
    setIsLoading(true);
    try {
      if (isLogin) {
        await onLogin(email, password);
      } else {
        if (!fullName.trim()) {
          throw new Error('Введите имя');
        }
        await onRegister(email, password, fullName);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка');
    } finally {
      setIsLoading(false);
    }
  };

  const inputClass = "w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1 dark:text-gray-300";

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-6 sm:mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 sm:w-16 sm:h-16 bg-white rounded-2xl shadow-lg mb-3 sm:mb-4">
            <Wallet className="w-7 h-7 sm:w-8 sm:h-8 text-blue-600" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white">FinanceApp</h1>
          <p className="text-blue-200 mt-1 sm:mt-2 text-sm sm:text-base">Управление личными финансами</p>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-5 sm:p-8 dark:bg-gray-800">
          <h2 className="text-xl sm:text-2xl font-bold text-gray-800 text-center mb-4 sm:mb-6 dark:text-white">
            {isLogin ? 'Вход в аккаунт' : 'Регистрация'}
          </h2>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm dark:bg-red-900/30 dark:border-red-700 dark:text-red-400">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
              <div>
                <label className={labelClass}>Имя</label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className={inputClass}
                    placeholder="Ваше имя"
                  />
                </div>
              </div>
            )}

            <div>
              <label className={labelClass}>Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                  placeholder="example@mail.ru"
                  required
                />
              </div>
            </div>

            <div>
              <label className={labelClass}>Пароль</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white dark:placeholder-gray-400"
                  placeholder="••••••••"
                  required
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {/* Согласие на обработку персональных данных - только при регистрации */}
            {!isLogin && (
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setAgreedToTerms(!agreedToTerms)}
                  className="flex items-start gap-3 text-left w-full group"
                >
                  <div className="mt-0.5 shrink-0">
                    {agreedToTerms ? (
                      <CheckSquare className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                    ) : (
                      <Square className="w-5 h-5 text-gray-400 group-hover:text-gray-500" />
                    )}
                  </div>
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    Нажимая кнопку «Зарегистрироваться», я даю своё согласие на обработку моих персональных данных и принимаю условия{' '}
                    <span
                      onClick={(e) => {
                        e.stopPropagation();
                        setShowPrivacyPolicy(true);
                      }}
                      className="text-blue-600 hover:text-blue-700 underline dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      Политики конфиденциальности
                    </span>
                  </span>
                </button>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || (!isLogin && !agreedToTerms)}
              className="w-full py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  {isLogin ? 'Вход...' : 'Регистрация...'}
                </>
              ) : (
                isLogin ? 'Войти' : 'Зарегистрироваться'
              )}
            </button>
          </form>

          <div className="mt-5 sm:mt-6 text-center">
            <button
              onClick={() => { setIsLogin(!isLogin); setError(null); setAgreedToTerms(false); }}
              className="text-blue-600 hover:text-blue-700 font-medium dark:text-blue-400 dark:hover:text-blue-300 text-sm sm:text-base"
            >
              {isLogin ? 'Нет аккаунта? Зарегистрироваться' : 'Уже есть аккаунт? Войти'}
            </button>
          </div>
        </div>

        {/* Features */}
        <div className="mt-6 sm:mt-8 grid grid-cols-3 gap-2 sm:gap-4 text-center text-white">
          <div className="p-2 sm:p-3">
            <div className="text-xl sm:text-2xl mb-1">📊</div>
            <div className="text-xs text-blue-200">Аналитика</div>
          </div>
          <div className="p-2 sm:p-3">
            <div className="text-xl sm:text-2xl mb-1">🔔</div>
            <div className="text-xs text-blue-200">Напоминания</div>
          </div>
          <div className="p-2 sm:p-3">
            <div className="text-xl sm:text-2xl mb-1">🏦</div>
            <div className="text-xs text-blue-200">Т-Банк</div>
          </div>
        </div>
      </div>

      {/* Модальное окно с политикой конфиденциальности */}
      {showPrivacyPolicy && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setShowPrivacyPolicy(false)}
        >
          <div 
            className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 sm:p-6 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg sm:text-xl font-bold text-gray-800 dark:text-white">
                Согласие на обработку персональных данных
              </h3>
              <button 
                onClick={() => setShowPrivacyPolicy(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-4 sm:p-6 overflow-y-auto max-h-[60vh] text-sm sm:text-base text-gray-600 dark:text-gray-300 space-y-4">
              <p>
                Настоящим я, субъект персональных данных, свободно, своей волей и в своём интересе 
                даю согласие на обработку моих персональных данных, предоставленных при регистрации 
                в сервисе FinanceApp.
              </p>
              
              <h4 className="font-semibold text-gray-800 dark:text-white">1. Перечень персональных данных:</h4>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Фамилия, имя, отчество</li>
                <li>Адрес электронной почты</li>
                <li>Данные о финансовых операциях</li>
              </ul>

              <h4 className="font-semibold text-gray-800 dark:text-white">2. Цели обработки:</h4>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Предоставление доступа к функциям сервиса</li>
                <li>Идентификация пользователя</li>
                <li>Отправка уведомлений и напоминаний</li>
                <li>Формирование аналитики и отчётов</li>
                <li>Улучшение качества сервиса</li>
              </ul>

              <h4 className="font-semibold text-gray-800 dark:text-white">3. Способы обработки:</h4>
              <p>
                Обработка персональных данных осуществляется с использованием средств автоматизации 
                и без использования таких средств, включает сбор, запись, систематизацию, накопление, 
                хранение, уточнение, извлечение, использование, передачу, обезличивание, блокирование, 
                удаление, уничтожение персональных данных.
              </p>

              <h4 className="font-semibold text-gray-800 dark:text-white">4. Срок действия согласия:</h4>
              <p>
                Согласие действует с момента его предоставления и до момента отзыва. 
                Отзыв согласия может быть осуществлён путём направления соответствующего 
                уведомления на электронную почту администрации сервиса или удаления аккаунта.
              </p>

              <h4 className="font-semibold text-gray-800 dark:text-white">5. Безопасность данных:</h4>
              <p>
                Оператор принимает необходимые правовые, организационные и технические меры 
                для защиты персональных данных от неправомерного или случайного доступа к ним, 
                уничтожения, изменения, блокирования, копирования, предоставления, 
                распространения персональных данных.
              </p>

              <p className="text-xs text-gray-500 dark:text-gray-400 pt-4 border-t border-gray-200 dark:border-gray-700">
                Обработка персональных данных осуществляется в соответствии с Федеральным законом 
                от 27.07.2006 № 152-ФЗ «О персональных данных».
              </p>
            </div>
            <div className="p-4 sm:p-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowPrivacyPolicy(false)}
                className="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
