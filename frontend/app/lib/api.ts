export type Role = 'user' | 'seller' | 'admin';

export type Product = {
  id: string;
  name: string;
  description: string;
  category: string;
  price: number;
  quantity: number;
  image: string;
  seller_id: string;
  art?: string;
  tone?: string;
};

export type Notification = {
  id: string;
  user_id: string;
  message: Record<string, unknown>;
  status: string;
  created_at: string;
};

export type UserProfile = {
  id: string;
  email: string;
  phone_number: string;
  balance: number;
  role: Role;
};

export type Balance = {
  balance: number;
};

export type Payment = {
  id: string;
  user_id: string;
  order_id: string;
  status: string;
  amount: number;
  created_at: string;
};

export type OrderItem = {
  id: string;
  order_id: string;
  product_id: string;
  product_name: string;
  unit_price: number;
  quantity: number;
};

export type Order = {
  id: string;
  user_id: string;
  status: string;
  total_amount: number;
  created_at: string;
  items: OrderItem[];
};

export type Analytics = {
  orders_total: number;
  successful_payments: number;
  failed_payments: number;
  cancelled_payments: number;
  refunded_payments: number;
  gross_revenue: number;
  refunded_amount: number;
  net_revenue: number;
  average_payment_amount: number;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8080/v1';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, { ...options, headers, credentials: 'include' });
  if (!response.ok) {
    let message = 'Не удалось выполнить запрос';
    try { message = (await response.json()).detail ?? message; } catch { /* empty response */ }
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function readToken(token: string): { sub: string; role: Role } | null {
  try {
    const payload = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const parsed = JSON.parse(decodeURIComponent(escape(atob(payload))));
    if (!['user', 'seller', 'admin'].includes(parsed.role) || !parsed.sub) return null;
    return { sub: parsed.sub, role: parsed.role };
  } catch { return null; }
}
