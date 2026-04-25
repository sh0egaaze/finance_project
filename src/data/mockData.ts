import { Transaction, Category, Reminder, CurrencyRate, MonthlyStats, CategoryExpense, Prediction, SavingTip } from '../types';

export const categories: Category[] = [
  { id: '1', name: 'Еда', icon: '🍔', color: '#FF6B6B' },
  { id: '2', name: 'Транспорт', icon: '🚗', color: '#4ECDC4' },
  { id: '3', name: 'Развлечения', icon: '🎮', color: '#9B59B6' },
  { id: '4', name: 'Покупки', icon: '🛍️', color: '#F39C12' },
  { id: '5', name: 'ЖКХ', icon: '🏠', color: '#3498DB' },
  { id: '6', name: 'Здоровье', icon: '💊', color: '#E74C3C' },
  { id: '7', name: 'Образование', icon: '📚', color: '#1ABC9C' },
  { id: '8', name: 'Подписки', icon: '📱', color: '#8E44AD' },
  { id: '9', name: 'Рестораны', icon: '🍽️', color: '#E67E22' },
  { id: '10', name: 'Переводы', icon: '💸', color: '#2ECC71' },
];

export const transactions: Transaction[] = [
  { id: '1', amount: -1250, description: 'Пятёрочка', category: categories[0], date: '2025-01-15T10:30:00', source: 'tbank', merchantName: 'Пятёрочка' },
  { id: '2', amount: -350, description: 'Яндекс.Такси', category: categories[1], date: '2025-01-15T09:15:00', source: 'tbank', merchantName: 'Яндекс Такси' },
  { id: '3', amount: -2500, description: 'Steam - покупка игры', category: categories[2], date: '2025-01-14T20:00:00', source: 'tbank', merchantName: 'Steam' },
  { id: '4', amount: -150, description: 'Булочка в кофейне', category: categories[0], date: '2025-01-14T12:30:00', source: 'cash' },
  { id: '5', amount: -4500, description: 'Wildberries', category: categories[3], date: '2025-01-13T15:45:00', source: 'tbank', merchantName: 'Wildberries' },
  { id: '6', amount: -6800, description: 'Оплата ЖКХ', category: categories[4], date: '2025-01-10T11:00:00', source: 'tbank', merchantName: 'МосОблЕИРЦ' },
  { id: '7', amount: -890, description: 'Аптека Горздрав', category: categories[5], date: '2025-01-09T14:20:00', source: 'tbank', merchantName: 'Горздрав' },
  { id: '8', amount: -1990, description: 'Skillbox - подписка', category: categories[6], date: '2025-01-08T10:00:00', source: 'tbank', merchantName: 'Skillbox' },
  { id: '9', amount: -199, description: 'Яндекс.Плюс', category: categories[7], date: '2025-01-05T00:00:00', source: 'tbank', merchantName: 'Яндекс' },
  { id: '10', amount: -2300, description: 'Ресторан Тануки', category: categories[8], date: '2025-01-04T19:30:00', source: 'tbank', merchantName: 'Тануки', isSuspicious: true },
  { id: '11', amount: 75000, description: 'Зарплата', category: categories[9], date: '2025-01-01T10:00:00', source: 'tbank', merchantName: 'ООО Компания' },
  { id: '12', amount: -15000, description: 'Подозрительный перевод', category: categories[9], date: '2025-01-03T03:45:00', source: 'tbank', isSuspicious: true },
  { id: '13', amount: -780, description: 'Магнит', category: categories[0], date: '2025-01-12T18:00:00', source: 'tbank', merchantName: 'Магнит' },
  { id: '14', amount: -450, description: 'Метро - проездной', category: categories[1], date: '2025-01-11T08:30:00', source: 'tbank', merchantName: 'Московский метрополитен' },
  { id: '15', amount: -3200, description: 'Ozon', category: categories[3], date: '2025-01-07T16:15:00', source: 'tbank', merchantName: 'Ozon' },
];

export const reminders: Reminder[] = [
  { id: '1', title: 'Оплата коммунальных услуг', frequency: 'monthly', nextDate: '2025-02-10', isActive: true },
  { id: '2', title: 'Вернуть долг Саше', amount: 5000, frequency: 'once', nextDate: '2025-01-25', remainingRepeats: 1, isActive: true },
  { id: '3', title: 'Подписка Яндекс.Плюс', amount: 199, frequency: 'monthly', nextDate: '2025-02-05', isActive: true },
  { id: '4', title: 'Страховка автомобиля', amount: 25000, frequency: 'yearly', nextDate: '2025-06-15', isActive: true },
  { id: '5', title: 'Интернет Ростелеком', amount: 750, frequency: 'monthly', nextDate: '2025-01-28', isActive: true },
];

export const currencyRates: CurrencyRate[] = [
  { code: 'USD', name: 'Доллар США', rate: 89.50, change: 0.35, flag: '🇺🇸' },
  { code: 'EUR', name: 'Евро', rate: 97.20, change: -0.15, flag: '🇪🇺' },
  { code: 'CNY', name: 'Китайский юань', rate: 12.35, change: 0.08, flag: '🇨🇳' },
  { code: 'GBP', name: 'Фунт стерлингов', rate: 113.45, change: 0.52, flag: '🇬🇧' },
  { code: 'JPY', name: 'Японская иена', rate: 0.58, change: -0.01, flag: '🇯🇵' },
];

export const monthlyStats: MonthlyStats[] = [
  { month: 'Авг', income: 75000, expenses: 52000, savings: 23000 },
  { month: 'Сен', income: 78000, expenses: 58000, savings: 20000 },
  { month: 'Окт', income: 75000, expenses: 48000, savings: 27000 },
  { month: 'Ноя', income: 82000, expenses: 61000, savings: 21000 },
  { month: 'Дек', income: 95000, expenses: 78000, savings: 17000 },
  { month: 'Янв', income: 75000, expenses: 36909, savings: 38091 },
];

export const categoryExpenses: CategoryExpense[] = [
  { category: 'Еда', amount: 12500, percentage: 28, color: '#FF6B6B' },
  { category: 'ЖКХ', amount: 6800, percentage: 18, color: '#3498DB' },
  { category: 'Покупки', amount: 7700, percentage: 17, color: '#F39C12' },
  { category: 'Развлечения', amount: 4500, percentage: 10, color: '#9B59B6' },
  { category: 'Транспорт', amount: 3200, percentage: 7, color: '#4ECDC4' },
  { category: 'Подписки', amount: 2189, percentage: 5, color: '#8E44AD' },
  { category: 'Рестораны', amount: 2300, percentage: 5, color: '#E67E22' },
  { category: 'Другое', amount: 4720, percentage: 10, color: '#95A5A6' },
];

export const predictions: Prediction[] = [
  { category: 'Еда', predicted: 14200, current: 12500, trend: 'up' },
  { category: 'Транспорт', predicted: 3800, current: 3200, trend: 'up' },
  { category: 'ЖКХ', predicted: 6800, current: 6800, trend: 'stable' },
  { category: 'Развлечения', predicted: 3200, current: 4500, trend: 'down' },
  { category: 'Покупки', predicted: 5500, current: 7700, trend: 'down' },
  { category: 'Подписки', predicted: 2200, current: 2189, trend: 'stable' },
];

export const savingTips: SavingTip[] = [
  {
    id: '1',
    title: 'Сократите расходы на рестораны',
    description: 'Вы тратите на рестораны больше среднего. Попробуйте готовить дома чаще.',
    potentialSaving: 1500,
    category: 'Рестораны'
  },
  {
    id: '2',
    title: 'Оптимизируйте подписки',
    description: 'У вас активно 3 стриминговых сервиса. Возможно, стоит оставить один.',
    potentialSaving: 600,
    category: 'Подписки'
  },
  {
    id: '3',
    title: 'Используйте кэшбэк',
    description: 'Оплачивайте покупки картой с кэшбэком в категории "Супермаркеты".',
    potentialSaving: 800,
    category: 'Еда'
  },
  {
    id: '4',
    title: 'Планируйте крупные покупки',
    description: 'Отложите покупки до распродаж и используйте промокоды.',
    potentialSaving: 2000,
    category: 'Покупки'
  },
];

// Функция для "умной" категоризации (имитация нейросети)
export function categorizeTransaction(description: string): Category {
  const lowerDesc = description.toLowerCase();
  
  const keywords: Record<string, string[]> = {
    '1': ['еда', 'продукт', 'магазин', 'пятёрочка', 'магнит', 'перекрёсток', 'ашан', 'лента', 'дикси', 'булочк', 'хлеб', 'молоко'],
    '2': ['такси', 'яндекс.такси', 'uber', 'метро', 'автобус', 'бензин', 'азс', 'транспорт', 'поезд', 'ржд'],
    '3': ['игр', 'steam', 'playstation', 'xbox', 'кино', 'театр', 'концерт', 'развлечен'],
    '4': ['wildberries', 'ozon', 'aliexpress', 'amazon', 'покупк', 'магазин', 'одежда', 'обувь'],
    '5': ['жкх', 'коммунал', 'электричество', 'газ', 'вода', 'отопление', 'квартплата'],
    '6': ['аптек', 'лекарств', 'врач', 'клиник', 'больниц', 'здоров', 'медицин'],
    '7': ['курс', 'обучен', 'skillbox', 'coursera', 'udemy', 'книг', 'образован'],
    '8': ['подписк', 'netflix', 'spotify', 'яндекс.плюс', 'apple', 'google'],
    '9': ['ресторан', 'кафе', 'бар', 'кофейн', 'суши', 'пицц', 'бургер', 'тануки', 'макдональдс'],
    '10': ['перевод', 'перевел', 'долг', 'зарплата', 'возврат'],
  };
  
  for (const [categoryId, words] of Object.entries(keywords)) {
    if (words.some(word => lowerDesc.includes(word))) {
      return categories.find(c => c.id === categoryId) || categories[0];
    }
  }
  
  return categories[3]; // По умолчанию - Покупки
}
