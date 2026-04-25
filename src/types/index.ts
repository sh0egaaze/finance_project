export interface Transaction {
  id: string;
  amount: number;
  description: string;
  category: Category;
  date: string;
  source: 'tbank' | 'manual' | 'cash';
  isSuspicious?: boolean;
  merchantName?: string;
}

export interface Category {
  id: string;
  name: string;
  icon: string;
  color: string;
}

export interface Reminder {
  id: string;
  title: string;
  amount?: number;
  frequency: 'once' | 'daily' | 'weekly' | 'monthly' | 'yearly';
  nextDate: string;
  repeatCount?: number; // undefined = бесконечно
  remainingRepeats?: number;
  isActive: boolean;
}

export interface CurrencyRate {
  code: string;
  name: string;
  rate: number;
  change: number;
  flag: string;
}

export interface MonthlyStats {
  month: string;
  income: number;
  expenses: number;
  savings: number;
}

export interface CategoryExpense {
  category: string;
  amount: number;
  percentage: number;
  color: string;
}

export interface Prediction {
  category: string;
  predicted: number;
  current: number;
  trend: 'up' | 'down' | 'stable';
}

export interface SavingTip {
  id: string;
  title: string;
  description: string;
  potentialSaving: number;
  category: string;
}
