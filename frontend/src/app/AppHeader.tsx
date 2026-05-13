'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function AppHeader() {
  const path = usePathname();
  const onDash = path === '/';

  return (
    <header className="hdr">
      <Link href="/" className="logo">
        <div className="logo-orb">✦</div>
        Creative Intelligence
      </Link>
      <nav className="hdr-nav">
        <Link href="/" className={`nav-btn${onDash ? ' on' : ''}`}>Dashboard</Link>
      </nav>
    </header>
  );
}
