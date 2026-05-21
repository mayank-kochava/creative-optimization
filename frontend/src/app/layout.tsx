import type { Metadata } from 'next';
import './globals.css';
import AntdProviders from './AntdProviders';
import AppHeader from './AppHeader';

export const metadata: Metadata = {
  title: 'Kochava Creative Optimiser',
  description: 'AI-powered ad creative analysis',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AntdProviders>
          <AppHeader />
          <main>{children}</main>
        </AntdProviders>
      </body>
    </html>
  );
}
