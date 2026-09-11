'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Analytics, api, Balance, Notification, Order, Payment, Product, readToken, Role, UserProfile } from './lib/api';

type View = 'catalog' | 'orders' | 'seller' | 'admin' | 'checkout' | 'notifications';
type Cart = Record<string, number>;

const demoProducts: Product[] = [
  { id:'1', seller_id:'demo-seller', name:'Беспроводные наушники', description:'Лёгкие полноразмерные наушники с активным шумоподавлением и чистым объёмным звуком.', category:'Электроника', price:12990, quantity:18, image:'', art:'🎧', tone:'blue' },
  { id:'2', seller_id:'demo-seller', name:'Смарт-часы Active Pro', description:'Здоровье, тренировки и уведомления на ярком AMOLED-экране.', category:'Электроника', price:15990, quantity:12, image:'', art:'⌚', tone:'violet' },
  { id:'3', seller_id:'demo-seller', name:'Робот-пылесос SmartClean', description:'Умная навигация, влажная уборка и управление со смартфона.', category:'Дом', price:19990, quantity:7, image:'', art:'◉', tone:'mint' },
  { id:'4', seller_id:'demo-seller', name:'Очиститель воздуха AirPure', description:'Тихая фильтрация воздуха для комнат площадью до 35 м².', category:'Дом', price:9990, quantity:15, image:'', art:'◫', tone:'sky' },
  { id:'5', seller_id:'demo-seller', name:'Коврик для йоги ProFit', description:'Нескользящий коврик с комфортной толщиной 6 мм.', category:'Спорт', price:1590, quantity:42, image:'', art:'▬', tone:'peach' },
  { id:'6', seller_id:'demo-seller', name:'Гантели наборные 10 кг', description:'Компактный набор для домашних силовых тренировок.', category:'Спорт', price:3990, quantity:28, image:'', art:'🏋', tone:'slate' },
  { id:'7', seller_id:'demo-seller', name:'Спортивная бутылка 750 мл', description:'Лёгкая бутылка с герметичной крышкой и удобным хватом.', category:'Спорт', price:990, quantity:63, image:'', art:'♙', tone:'blue' },
  { id:'8', seller_id:'demo-seller', name:'Скакалка SpeedJump', description:'Скоростная скакалка с регулируемой длиной троса.', category:'Спорт', price:890, quantity:56, image:'', art:'〰', tone:'violet' },
];

const demoOrders: Order[] = [
  { id:'10024', user_id:'demo', status:'paid', total_amount:28480, created_at:'2026-08-22T14:35:00Z', items:[
    { id:'a', order_id:'10024', product_id:'1', product_name:'Беспроводные наушники', unit_price:12990, quantity:1 },
    { id:'b', order_id:'10024', product_id:'2', product_name:'Смарт-часы Active Pro', unit_price:15990, quantity:1 },
  ]},
  { id:'10017', user_id:'demo', status:'waiting_payment', total_amount:9990, created_at:'2026-08-20T11:20:00Z', items:[
    { id:'c', order_id:'10017', product_id:'4', product_name:'Очиститель воздуха AirPure', unit_price:9990, quantity:1 },
  ]},
];

const demoAnalytics: Analytics = { orders_total:1284, successful_payments:1056, failed_payments:74, cancelled_payments:44, refunded_payments:31, gross_revenue:12480000, refunded_amount:342000, net_revenue:12138000, average_payment_amount:11818 };
const statusNames: Record<string,string> = { created:'Создан', waiting_payment:'Ожидает оплаты', paid:'Оплачен', shipped:'Передан в доставку', delivered:'Доставлен', closed:'Завершён', cancelled:'Отменён', failed:'Ошибка' };
const artByCategory: Record<string,string> = { Электроника:'⌁', Дом:'◫', Спорт:'●' };
const money = (value:number) => `${new Intl.NumberFormat('ru-RU').format(value)} ₽`;

export default function Home() {
  const [view, setView] = useState<View>('catalog');
  const [products, setProducts] = useState<Product[]>(demoProducts);
  const [orders, setOrders] = useState<Order[]>(demoOrders);
  const [sellerOrders, setSellerOrders] = useState<Order[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [analytics, setAnalytics] = useState<Analytics>(demoAnalytics);
  const [cart, setCart] = useState<Cart>({ '1':1, '2':1 });
  const [category, setCategory] = useState('Все');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Product|null>(null);
  const [authOpen, setAuthOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [authMode, setAuthMode] = useState<'login'|'register'>('login');
  const [token, setToken] = useState('');
  const [role, setRole] = useState<Role>('user');
  const [userId, setUserId] = useState('');
  const [balance, setBalance] = useState(0);
  const [email, setEmail] = useState('demo@microshop.ru');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);
  const [payingOrderId, setPayingOrderId] = useState('');

  useEffect(() => {
    // Browser-only state is restored after hydration so server and client markup match.
    const hydrationTimer = window.setTimeout(() => {
      const savedToken = localStorage.getItem('microshop_token') ?? '';
      const savedCart = localStorage.getItem('microshop_cart');
      if (savedCart) try { setCart(JSON.parse(savedCart)); } catch { /* keep defaults */ }
      if (savedToken) {
        const session = readToken(savedToken);
        if (session) { setToken(savedToken); setRole(session.role); setUserId(session.sub); }
      }
    }, 0);

    api<Product[]>('/products').then(setProducts).catch(() => undefined);

    return () => window.clearTimeout(hydrationTimer);
  }, []);

  useEffect(() => { localStorage.setItem('microshop_cart', JSON.stringify(cart)); }, [cart]);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(''), 2500);
    return () => window.clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    if (!token) return;
    if (view === 'orders') api<Order[]>('/orders', {}, token).then(setOrders).catch(() => undefined);
    if (view === 'notifications' && userId) api<Notification[]>(`/notifications/users/${userId}`, {}, token).then(setNotifications).catch(() => undefined);
    if (view === 'seller' && role === 'seller') {
      api<Order[]>('/orders/sales', {}, token).then(setSellerOrders).catch(() => undefined);
      if (userId) api<Notification[]>(`/notifications/users/${userId}`, {}, token).then(setNotifications).catch(() => undefined);
    }
    if (view === 'admin' && role === 'admin') api<Analytics>('/analytics/overview', {}, token).then(setAnalytics).catch(() => undefined);
  }, [view, token, role, userId]);
  useEffect(() => {
    if (!token || token.startsWith('demo-')) return;
    api<UserProfile>('/auth/me', {}, token).then((profile) => setBalance(profile.balance)).catch(() => undefined);
  }, [token]);

  const cartItems = useMemo(() => Object.entries(cart).flatMap(([id, quantity]) => {
    const product = products.find((item) => item.id === id);
    return product ? [{ product, quantity }] : [];
  }), [cart, products]);
  const cartCount = cartItems.reduce((sum,item) => sum + item.quantity, 0);
  const cartTotal = cartItems.reduce((sum,item) => sum + item.product.price * item.quantity, 0);
  const categories = ['Все', ...Array.from(new Set(products.map((product) => product.category)))];
  const visibleProducts = products.filter((product) => (category === 'Все' || product.category === category) && product.name.toLowerCase().includes(search.toLowerCase()));

  function navigate(next: View) {
    if (['orders','checkout','notifications'].includes(next) && !token) { setAuthOpen(true); setNotice('Войдите, чтобы продолжить'); return; }
    if (next === 'seller' && role !== 'seller') return;
    if (next === 'admin' && role !== 'admin') return;
    setView(next); setProfileOpen(false); window.scrollTo({ top:0, behavior:'smooth' });
  }

  function addToCart(product: Product) {
    setCart((current) => ({ ...current, [product.id]: Math.min((current[product.id] ?? 0) + 1, product.quantity) }));
    setNotice(`${product.name} добавлен в корзину`);
  }

  function setCartQuantity(id:string, quantity:number) {
    setCart((current) => { const next = { ...current }; if (quantity <= 0) delete next[id]; else next[id] = quantity; return next; });
  }

  async function submitAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); setNotice('');
    const data = new FormData(event.currentTarget);
    try {
      if (authMode === 'register') {
        await api('/auth/register', { method:'POST', body:JSON.stringify({ email:data.get('email'), phone_number:data.get('phone'), password:data.get('password') }) });
      }
      const response = await api<{access_token:string}>('/auth/login/email', { method:'POST', body:JSON.stringify({ email:data.get('email'), password:data.get('password') }) });
      const session = readToken(response.access_token);
      if (!session) throw new Error('Некорректный токен');
      localStorage.setItem('microshop_token', response.access_token); setToken(response.access_token); setRole(session.role); setUserId(session.sub); setEmail(String(data.get('email'))); setAuthOpen(false); setNotice('Вы успешно вошли');
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Не удалось войти'); }
    finally { setLoading(false); }
  }

  function useDemo(nextRole: Role) {
    setRole(nextRole); setToken(`demo-${nextRole}`); setUserId(nextRole === 'seller' ? 'demo-seller' : `demo-${nextRole}`); setBalance(50000); setEmail(`${nextRole}@microshop.demo`); setAuthOpen(false); setProfileOpen(false); setNotice(`Включён демо-режим: ${nextRole}`);
  }

  function logout() { localStorage.removeItem('microshop_token'); setToken(''); setUserId(''); setBalance(0); setRole('user'); setView('catalog'); setProfileOpen(false); }

  async function changeBalance(operation:'deposit'|'withdraw', amount:number) {
    try {
      const result = token.startsWith('demo-')
        ? { balance:Math.max(0, balance + (operation === 'deposit' ? amount : -amount)) }
        : await api<Balance>(`/auth/balance/${operation}`, { method:'POST', body:JSON.stringify({ amount }) }, token);
      setBalance(result.balance);
      setNotice(operation === 'deposit' ? 'Баланс пополнен' : 'Средства выведены');
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Не удалось изменить баланс'); }
  }

  async function payOrder(order:Order) {
    setPayingOrderId(order.id);
    try {
      if (token.startsWith('demo-')) {
        if (balance < order.total_amount) throw new Error('Недостаточно средств');
        setBalance((current) => current - order.total_amount);
        setOrders((current) => current.map((item) => item.id === order.id ? { ...item, status:'paid' } : item));
        setNotice('Заказ оплачен');
        return;
      }

      let payment:Payment|undefined;
      for (let attempt=0; attempt<6 && !payment; attempt+=1) {
        const payments = await api<Payment[]>(`/payments?order_id=${encodeURIComponent(order.id)}`, {}, token);
        payment = payments.find((item) => ['pending','processing','failed'].includes(item.status));
        if (!payment) await new Promise((resolve) => window.setTimeout(resolve, 400));
      }
      if (!payment) throw new Error('Платёж ещё не создан. Попробуйте через несколько секунд');

      const endpoint = payment.status === 'failed' ? 'retry' : 'complete';
      const completed = await api<Payment>(`/payments/${payment.id}/${endpoint}`, { method:'POST' }, token);
      const currentBalance = await api<Balance>('/auth/balance', {}, token);
      setBalance(currentBalance.balance);
      if (completed.status === 'succeeded') {
        setOrders((current) => current.map((item) => item.id === order.id ? { ...item, status:'paid' } : item));
        setNotice('Заказ оплачен');
      } else {
        setNotice('Недостаточно средств для оплаты');
      }
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Не удалось выполнить оплату'); }
    finally { setPayingOrderId(''); }
  }

  async function createOrder(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true);
    try {
      const created = token.startsWith('demo-') ? { ...demoOrders[0], id:String(Date.now()).slice(-6), total_amount:cartTotal, status:'created', created_at:new Date().toISOString(), items:cartItems.map(({product,quantity}, index) => ({ id:`new-${index}`, order_id:'', product_id:product.id, product_name:product.name, unit_price:product.price, quantity })) } : await api<Order>('/orders', { method:'POST', body:JSON.stringify({ items:cartItems.map(({product,quantity}) => ({ product_id:product.id, quantity })) }) }, token);
      setOrders((current) => [created, ...current]); setCart({}); setView('orders'); setNotice('Заказ успешно создан');
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Не удалось создать заказ'); }
    finally { setLoading(false); }
  }

  async function createProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setLoading(true); const data = new FormData(event.currentTarget);
    const draft = { name:String(data.get('name')), description:String(data.get('description')), category:String(data.get('category')), price:Number(data.get('price')), quantity:Number(data.get('quantity')), image:String(data.get('image') ?? '') };
    try {
      const created = token.startsWith('demo-') ? { ...draft, id:`demo-${Date.now()}`, seller_id:userId, art:artByCategory[draft.category] ?? '◈', tone:'blue' } : await api<Product>('/products', { method:'POST', body:JSON.stringify(draft) }, token);
      setProducts((current) => [created, ...current]); event.currentTarget.reset(); setNotice('Товар опубликован');
    } catch (error) { setNotice(error instanceof Error ? error.message : 'Не удалось создать товар'); }
    finally { setLoading(false); }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <button className="brand brand-button" onClick={() => navigate('catalog')}><span className="brand-mark">M</span><span>MicroShop</span></button>
        <label className="search"><span aria-hidden="true">⌕</span><input aria-label="Поиск товаров" placeholder="Поиск товаров" value={search} onChange={(event) => { setSearch(event.target.value); setView('catalog'); }} /></label>
        <nav className="header-actions" aria-label="Быстрые действия">
          <button className="icon-button" aria-label="Уведомления" onClick={() => navigate('notifications')}>♧</button>
          <div className="profile-wrap">
            <button className="profile-button" aria-label="Профиль" onClick={() => setProfileOpen(!profileOpen)}><span>{token ? email.slice(0,2).toUpperCase() : 'Войти'}</span></button>
            {profileOpen && <div className="profile-menu">
              {token ? <><strong>{email}</strong><small className={`role-badge ${role}`}>{role}</small><div className="profile-balance"><small>Баланс</small><strong>{money(balance)}</strong><div><button onClick={() => changeBalance('deposit',10000)}>+10 000 ₽</button><button onClick={() => changeBalance('withdraw',1000)}>−1 000 ₽</button></div></div><button onClick={() => navigate('orders')}>Мои заказы</button>{role === 'seller' && <button onClick={() => navigate('seller')}>Кабинет продавца</button>}{role === 'admin' && <button onClick={() => navigate('admin')}>Админ-панель</button>}<button className="danger-link" onClick={logout}>Выйти</button></> : <button className="primary-button" onClick={() => {setAuthOpen(true);setProfileOpen(false)}}>Войти</button>}
            </div>}
          </div>
          <button className="cart-button" aria-label={`Корзина, товаров: ${cartCount}`} onClick={() => navigate('checkout')}><span aria-hidden="true">🛒</span><b>{cartCount}</b></button>
        </nav>
      </header>

      {token && <nav className="role-nav" aria-label="Разделы приложения">
        <button className={view === 'catalog' ? 'active' : ''} onClick={() => navigate('catalog')}>Каталог</button>
        <button className={view === 'orders' ? 'active' : ''} onClick={() => navigate('orders')}>Мои заказы</button>
        <button className={view === 'notifications' ? 'active' : ''} onClick={() => navigate('notifications')}>Уведомления</button>
        {role === 'seller' && <button className={view === 'seller' ? 'active' : ''} onClick={() => navigate('seller')}>Кабинет продавца</button>}
        {role === 'admin' && <button className={view === 'admin' ? 'active' : ''} onClick={() => navigate('admin')}>Аналитика</button>}
        <span className={`role-badge ${role}`}>{role}</span>
      </nav>}

      {view === 'catalog' && <Catalog products={visibleProducts} categories={categories} category={category} setCategory={setCategory} addToCart={addToCart} select={setSelected} />}
      {view === 'checkout' && <Checkout items={cartItems} total={cartTotal} setQuantity={setCartQuantity} submit={createOrder} loading={loading} />}
      {view === 'orders' && <Orders orders={orders} pay={payOrder} payingOrderId={payingOrderId} />}
      {view === 'notifications' && <Notifications notifications={notifications} />}
      {view === 'seller' && role === 'seller' && <Seller products={token.startsWith('demo-') ? products : products.filter((product) => product.seller_id === userId)} orders={token.startsWith('demo-') ? demoOrders : sellerOrders} notifications={notifications} submit={createProduct} loading={loading} />}
      {view === 'admin' && role === 'admin' && <Admin analytics={analytics} products={products} />}

      {selected && <ProductModal product={selected} close={() => setSelected(null)} add={() => { addToCart(selected); setSelected(null); }} />}
      {authOpen && <AuthModal mode={authMode} setMode={setAuthMode} close={() => setAuthOpen(false)} submit={submitAuth} demo={useDemo} loading={loading} />}
      {notice && <div className="toast" role="status"><span>✓</span>{notice}</div>}
    </main>
  );
}

function Catalog({ products, categories, category, setCategory, addToCart, select }:{ products:Product[]; categories:string[]; category:string; setCategory:(value:string)=>void; addToCart:(product:Product)=>void; select:(product:Product)=>void }) {
  return <section className="catalog-wrap">
    <div className="catalog-heading"><div><p className="eyebrow">Умные покупки каждый день</p><h1>Всё нужное — в одном месте</h1><p>Техника, товары для дома и спорта с быстрой доставкой.</p></div><div className="promo-card"><span>Товар дня</span><strong>−20%</strong><small>на умные устройства</small></div></div>
    <div className="catalog-toolbar"><div className="category-tabs" role="tablist">{categories.map((item) => <button key={item} className={category === item ? 'active' : ''} onClick={() => setCategory(item)} role="tab" aria-selected={category === item}>{item}</button>)}</div><button className="sort-button">Сначала популярные <span>⌄</span></button></div>
    <div className="product-grid">{products.map((product) => <article className="product-card" key={product.id}><button className="favorite" aria-label="В избранное">♡</button><button className={`product-art ${product.tone ?? 'blue'}`} onClick={() => select(product)} aria-label={`Открыть ${product.name}`}><ProductImage product={product} /></button><p className="product-category">{product.category}</p><button className="product-title" onClick={() => select(product)}>{product.name}</button><strong className="product-price">{money(product.price)}</strong><p className="stock">В наличии: {product.quantity}</p><button className="primary-button" onClick={() => addToCart(product)}>В корзину</button></article>)}</div>
    {!products.length && <div className="empty-state"><span>⌕</span><h2>Ничего не найдено</h2><p>Попробуйте изменить запрос или категорию.</p></div>}
  </section>;
}

function ProductImage({ product }:{ product:Product }) {
  const [failed, setFailed] = useState(false);
  // Arbitrary seller URLs cannot use next/image without a fixed remote-host allowlist.
  if (product.image && !failed) return <img src={product.image} alt="" loading="lazy" onError={() => setFailed(true)} />; // eslint-disable-line @next/next/no-img-element
  return <span>{product.art ?? artByCategory[product.category] ?? '◈'}</span>;
}

function ProductModal({ product, close, add }:{ product:Product; close:()=>void; add:()=>void }) {
  return <div className="modal-backdrop" onMouseDown={close}><section className="modal product-modal" onMouseDown={(event) => event.stopPropagation()}><button className="modal-close" onClick={close}>×</button><div className={`detail-art ${product.tone ?? 'blue'}`}><ProductImage product={product} /></div><div className="detail-copy"><p className="breadcrumbs">Каталог · {product.category}</p><h2>{product.name}</h2><div className="rating">★★★★★ <span>4,8 · 128 отзывов</span></div><strong className="detail-price">{money(product.price)}</strong><p className="stock">В наличии: {product.quantity}</p><p className="description">{product.description}</p><button className="primary-button large" onClick={add}>Добавить в корзину</button><button className="secondary-button">♡ Добавить в избранное</button></div></section></div>;
}

function Checkout({ items, total, setQuantity, submit, loading }:{ items:{product:Product;quantity:number}[]; total:number; setQuantity:(id:string,q:number)=>void; submit:(event:FormEvent<HTMLFormElement>)=>void; loading:boolean }) {
  return <section className="page-wrap"><div className="page-title"><p className="eyebrow">Оформление</p><h1>Корзина</h1><p>{items.length ? `${items.length} позиции готовы к оформлению` : 'Добавьте товары из каталога'}</p></div>{items.length ? <form className="checkout-grid" onSubmit={submit}><div><section className="panel"><h2>Ваш заказ</h2>{items.map(({product,quantity}) => <div className="cart-row" key={product.id}><div className={`mini-art ${product.tone ?? 'blue'}`}>{product.art ?? '◈'}</div><div className="cart-name"><strong>{product.name}</strong><small>{money(product.price)}</small></div><div className="quantity"><button type="button" onClick={() => setQuantity(product.id,quantity-1)}>−</button><span>{quantity}</span><button type="button" onClick={() => setQuantity(product.id,quantity+1)}>+</button></div><strong>{money(product.price*quantity)}</strong><button className="remove" type="button" onClick={() => setQuantity(product.id,0)}>×</button></div>)}</section><section className="panel address"><h2>Адрес доставки</h2><div className="field-grid"><label>Получатель<input required defaultValue="Иван Иванов" /></label><label>Телефон<input required defaultValue="+7 (999) 123-45-67" /></label><label>Город<input required defaultValue="Москва" /></label><label>Адрес<input required defaultValue="ул. Ленина, д. 10" /></label></div><label>Комментарий<textarea placeholder="Например, позвонить перед доставкой" /></label></section></div><aside className="summary panel"><h2>Итого</h2><div><span>Товары</span><strong>{money(total)}</strong></div><div><span>Доставка</span><strong className="success">Бесплатно</strong></div><hr/><div className="summary-total"><span>Итого</span><strong>{money(total)}</strong></div><button className="primary-button large" disabled={loading}>{loading?'Создаём заказ…':'Оформить заказ'}</button><small>Нажимая кнопку, вы соглашаетесь с условиями оферты.</small></aside></form> : <div className="empty-state"><span>🛒</span><h2>Корзина пока пуста</h2><p>Вернитесь в каталог и выберите товары.</p></div>}</section>;
}

function Orders({ orders, pay, payingOrderId }:{ orders:Order[]; pay:(order:Order)=>void; payingOrderId:string }) {
  const steps = ['created','waiting_payment','paid','shipped','delivered'];
  return <section className="page-wrap"><div className="page-title"><p className="eyebrow">История покупок</p><h1>Мои заказы</h1><p>Следите за оплатой, сборкой и доставкой.</p></div><div className="orders-list">{orders.map((order) => { const current = Math.max(0,steps.indexOf(order.status)); return <article className="order-card" key={order.id}><div className="order-meta"><div><strong>Заказ №{order.id}</strong><small>{new Date(order.created_at).toLocaleDateString('ru-RU',{day:'numeric',month:'long',year:'numeric'})}</small></div><strong>{money(order.total_amount)}</strong><span className={`status ${order.status}`}>{statusNames[order.status] ?? order.status}</span></div><div className="order-progress">{steps.map((step,index) => <div className={index <= current ? 'done' : ''} key={step}><i>{index < current ? '✓' : index+1}</i><span>{statusNames[step]}</span></div>)}</div><div className="order-products">{order.items.map((item) => <span key={item.id}>{item.product_name} × {item.quantity}</span>)}</div>{order.status === 'waiting_payment' && <button className="primary-button order-pay" onClick={() => pay(order)} disabled={payingOrderId === order.id}>{payingOrderId === order.id ? 'Оплачиваем…' : `Оплатить ${money(order.total_amount)}`}</button>}</article>})}</div></section>;
}

function Notifications({ notifications }:{ notifications:Notification[] }) {
  return <section className="page-wrap"><div className="page-title"><p className="eyebrow">Центр событий</p><h1>Уведомления</h1><p>Изменения заказов и платежей появляются здесь.</p></div><div className="orders-list">{notifications.map((item) => <article className="panel notification-card" key={item.id}><div><strong>{notificationText(item.message)}</strong><small>{new Date(item.created_at).toLocaleString('ru-RU')}</small></div><span className={`status ${item.status}`}>{item.status}</span></article>)}</div>{!notifications.length && <div className="empty-state"><span>♧</span><h2>Уведомлений пока нет</h2><p>Мы сообщим о важных изменениях.</p></div>}</section>;
}

function notificationText(message: Record<string, unknown>) {
  const text = message.message ?? message.detail ?? message.event ?? message.status;
  return typeof text === 'string' ? text : JSON.stringify(message);
}

function Seller({ products, orders, notifications, submit, loading }:{ products:Product[]; orders:Order[]; notifications:Notification[]; submit:(event:FormEvent<HTMLFormElement>)=>void; loading:boolean }) {
  const [section, setSection] = useState<'overview'|'orders'|'products'|'notifications'>('products');
  const sections = [
    { id:'overview' as const, label:'Обзор', icon:'◫' },
    { id:'orders' as const, label:'Заказы', icon:'☷' },
    { id:'products' as const, label:'Товары', icon:'◇' },
    { id:'notifications' as const, label:'Уведомления', icon:'♧' },
  ];
  const titles = { overview:'Обзор', orders:'Заказы покупателей', products:'Товары', notifications:'Уведомления' };
  return <div className="dashboard-layout"><aside className="side-nav"><div className="side-brand"><span>M</span>MicroShop</div>{sections.map((item) => <button className={section===item.id?'active':''} key={item.id} onClick={() => setSection(item.id)}>{item.icon} {item.label}</button>)}</aside><section className="dashboard-main"><div className="dashboard-head"><div><p className="eyebrow">Кабинет продавца</p><h1>{titles[section]}</h1></div><span className="role-badge seller">seller</span></div>{section === 'overview' && <div className="metric-grid"><Metric label="Товаров" value={String(products.length)} delta="0%" icon="◇" blue/><Metric label="Заказов" value={String(orders.length)} delta="0%" icon="☷"/><Metric label="Уведомлений" value={String(notifications.length)} delta="0%" icon="♧"/></div>}{section === 'orders' && <SellerOrders orders={orders} />}{section === 'notifications' && <Notifications notifications={notifications} />}{section === 'products' && <div className="seller-grid"><form className="panel product-form" onSubmit={submit}><h2>Новый товар</h2><label>Название<input name="name" minLength={5} required placeholder="Например, беспроводные наушники" /></label><label>Описание<textarea name="description" required placeholder="Расскажите о главных преимуществах" /></label><div className="field-grid"><label>Категория<select name="category"><option>Электроника</option><option>Дом</option><option>Спорт</option></select></label><label>Цена, ₽<input name="price" type="number" min="0" required /></label><label>Остаток<input name="quantity" type="number" min="0" required /></label><label>Ссылка на изображение<input name="image" type="url" placeholder="https://…" /></label></div><button className="primary-button large" disabled={loading}>{loading?'Публикуем…':'Опубликовать товар'}</button></form><section className="panel inventory"><div className="panel-heading"><h2>Ваш каталог</h2><span>{products.length} товаров</span></div>{products.slice(0,6).map((product) => <div className="inventory-row" key={product.id}><div className={`mini-art ${product.tone ?? 'blue'}`}><ProductImage product={product} /></div><div><strong>{product.name}</strong><small>{product.category} · {product.quantity} шт.</small></div><strong>{money(product.price)}</strong><button>•••</button></div>)}</section></div>}</section></div>;
}

function SellerOrders({ orders }:{ orders:Order[] }) {
  return <div className="orders-list">{orders.map((order) => <article className="order-card" key={order.id}><div className="order-meta"><div><strong>Заказ №{order.id}</strong><small>{new Date(order.created_at).toLocaleDateString('ru-RU')}</small></div><strong>{money(order.total_amount)}</strong><span className={`status ${order.status}`}>{statusNames[order.status] ?? order.status}</span></div><div className="order-products">{order.items.map((item) => <span key={item.id}>{item.product_name} × {item.quantity}</span>)}</div></article>)}{!orders.length && <div className="empty-state"><span>☷</span><h2>Заказов пока нет</h2><p>Здесь появятся заказы с вашими товарами.</p></div>}</div>;
}

function Admin({ analytics, products }:{ analytics:Analytics; products:Product[] }) {
  const rate = Math.round((analytics.successful_payments / Math.max(1,analytics.successful_payments+analytics.failed_payments+analytics.cancelled_payments))*100);
  const chart = [48,44,52,61,55,64,50,46,58,67,54,49,62,70,57,52,65,73,60,56,69,76,63,59,72,66,78,70,68,75,81];
  return <div className="dashboard-layout"><aside className="side-nav"><div className="side-brand"><span>M</span>MicroShop</div>{['Обзор','Заказы','Товары','Платежи','Аналитика','Уведомления'].map((item,index) => <button className={index===4?'active':''} key={item}>{['◫','☷','◇','▤','▥','♧'][index]} {item}</button>)}</aside><section className="dashboard-main"><div className="dashboard-head"><div><p className="eyebrow">Администрирование</p><h1>Статистика магазина</h1></div><div className="period">1–31 августа 2026 <span>⌄</span></div></div><div className="metric-grid"><Metric label="Всего заказов" value={new Intl.NumberFormat('ru-RU').format(analytics.orders_total)} delta="12,3%" icon="▢" blue/><Metric label="Чистая выручка" value={money(analytics.net_revenue)} delta="15,7%" icon="₽"/><Metric label="Успешные платежи" value={new Intl.NumberFormat('ru-RU').format(analytics.successful_payments)} delta="10,8%" icon="✓"/><Metric label="Средний платёж" value={money(analytics.average_payment_amount)} delta="4,6%" icon="▤" blue/></div><div className="analytics-grid"><section className="panel revenue-panel"><div className="panel-heading"><h2>Динамика выручки</h2><div className="legend"><span className="blue-dot">Валовая</span><span className="green-dot">Чистая</span></div></div><div className="bar-chart">{chart.map((height,index) => <i key={index} style={{height:`${height}%`}}><b style={{height:`${Math.max(12,height-15)}%`}} /></i>)}</div><div className="axis"><span>1 авг.</span><span>11 авг.</span><span>21 авг.</span><span>31 авг.</span></div></section><section className="panel payment-panel"><h2>Платежи</h2><div className="donut" style={{background:`conic-gradient(#11a05a 0 ${rate}%,#ff5b5b ${rate}% ${Math.min(100,rate+6)}%,#f4b642 0)`}}><div><small>Успешность</small><strong>{rate}%</strong><small>возвратов 2,9%</small></div></div><div className="payment-legend"><span><i className="green-bg"/>Успешные <b>{analytics.successful_payments}</b></span><span><i className="red-bg"/>Неуспешные <b>{analytics.failed_payments}</b></span><span><i className="yellow-bg"/>Отменённые <b>{analytics.cancelled_payments}</b></span></div></section></div><section className="panel top-products"><div className="panel-heading"><h2>Топ товаров</h2><span>по выручке</span></div>{products.slice(0,4).map((product,index) => <div className="top-row" key={product.id}><b>{index+1}</b><div className={`mini-art ${product.tone ?? 'blue'}`}>{product.art ?? '◈'}</div><span>{product.name}</span><small>{186-index*29} заказов</small><strong>{money(product.price*(186-index*29))}</strong></div>)}</section></section></div>;
}

function Metric({ label,value,delta,icon,blue=false }:{label:string;value:string;delta:string;icon:string;blue?:boolean}) { return <article className="metric panel"><span className={blue?'blue-icon':''}>{icon}</span><div><small>{label}</small><strong>{value}</strong><em>↑ {delta} <i>к июлю</i></em></div></article>; }

function AuthModal({ mode,setMode,close,submit,demo,loading }:{mode:'login'|'register';setMode:(value:'login'|'register')=>void;close:()=>void;submit:(event:FormEvent<HTMLFormElement>)=>void;demo:(role:Role)=>void;loading:boolean}) {
  return <div className="modal-backdrop auth-bg" onMouseDown={close}><section className="modal auth-modal" onMouseDown={(event)=>event.stopPropagation()}><button className="modal-close" onClick={close}>×</button><div className="auth-logo"><span>M</span>MicroShop</div><p className="eyebrow">Добро пожаловать</p><h2>{mode==='login'?'Вход в аккаунт':'Создать аккаунт'}</h2><form onSubmit={submit}><label>Email<input name="email" type="email" required defaultValue="demo@microshop.ru" /></label>{mode==='register'&&<label>Номер телефона<input name="phone" required defaultValue="+79991234567" /></label>}<label>Пароль<input name="password" type="password" minLength={6} required defaultValue="password" /></label><button className="primary-button large" disabled={loading}>{loading?'Подождите…':mode==='login'?'Войти':'Зарегистрироваться'}</button></form><button className="auth-switch" onClick={()=>setMode(mode==='login'?'register':'login')}>{mode==='login'?'Нет аккаунта? Зарегистрироваться':'Уже есть аккаунт? Войти'}</button><div className="demo-separator"><span>Демо без backend</span></div><div className="demo-roles"><button onClick={()=>demo('user')}>Покупатель</button><button onClick={()=>demo('seller')}>Продавец</button><button onClick={()=>demo('admin')}>Админ</button></div></section></div>;
}
