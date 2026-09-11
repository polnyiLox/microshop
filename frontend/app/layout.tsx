import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: 'MicroShop — покупки без лишнего',
  description: 'Каталог товаров, заказы и кабинеты продавца и администратора MicroShop.',
  openGraph: {
    title: 'MicroShop',
    description: 'Покупки без лишнего',
    images: [{ url: '/og.png', width: 1200, height: 630, alt: 'MicroShop — покупки без лишнего' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'MicroShop',
    description: 'Покупки без лишнего',
    images: ['/og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
