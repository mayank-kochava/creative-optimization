import type { Metadata } from 'next';
import './globals.css';
import AntdProviders from './AntdProviders';

export const metadata: Metadata = {
  title: 'Creative Intelligence Platform',
  description: 'AI-powered ad creative analysis',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AntdProviders>{children}</AntdProviders>
      </body>
    </html>
  );
}
