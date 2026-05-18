'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function AppHeader() {
  const path = usePathname();
  return (
    <header className="hdr">
      <Link href="/" className="logo">
        <div className="logo-orb">✦</div>
        Creative Intelligence
      </Link>
      <nav className="hdr-nav">
        <Link href="/" className={`nav-btn${path === '/' ? ' on' : ''}`}>Dashboard</Link>
        <Link href="/campaigns" className={`nav-btn${path.startsWith('/campaigns') ? ' on' : ''}`}>Campaigns</Link>
        <Link href="/performance" className={`nav-btn${path === '/performance' ? ' on' : ''}`}>Performance</Link>
      </nav>
    </header>
  );
}
