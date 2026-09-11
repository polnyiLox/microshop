# MicroShop Frontend

Пользовательский интерфейс MicroShop для покупателя, продавца и администратора.
Frontend обращается только к API Gateway и не передаёт доверенные identity
headers напрямую во внутренние микросервисы.

## Возможности

- каталог, фильтрация товаров и корзина;
- регистрация и вход по access-токену;
- создание, просмотр и оплата заказов;
- пополнение и снятие средств;
- кабинет продавца с товарами, заказами и уведомлениями;
- административная сводка аналитики;
- уведомления пользователя;
- демонстрационный режим без запущенного backend.

## Технологии

- React 19 и TypeScript;
- Next.js 16 через Vinext/Vite;
- Tailwind CSS 4;
- контейнерная production-сборка под непривилегированным пользователем.

## Конфигурация

Создайте локальный файл окружения:

```powershell
Copy-Item .env.example .env.local
```

Доступны две публичные build-time переменные:

- `NEXT_PUBLIC_API_URL` — URL API Gateway с префиксом `/v1`;
- `NEXT_PUBLIC_SITE_URL` — внешний URL frontend.

Эти переменные попадают в браузерный bundle и не должны содержать секреты.

## Локальный запуск

Понадобится Node.js 22 или новее:

```powershell
npm ci
npm run dev
```

Приложение будет доступно на <http://localhost:3000>. Для работы с настоящими
данными API Gateway должен быть доступен по адресу из `NEXT_PUBLIC_API_URL`.

## Проверки и сборка

```powershell
npm run lint
npm run build
npm run start
```

Весь MicroShop вместе с frontend рекомендуется запускать из корня проекта:

```powershell
docker compose up --build
```
