'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  MessageSquare, BarChart2, BookOpen, Settings, Zap, Bell, Package
} from 'lucide-react';

const NAV_ITEMS = [
  { href: '/inbox', icon: MessageSquare, label: 'Inbox' },
  { href: '/dashboard', icon: BarChart2, label: 'Dashboard' },
  { href: '/warehouse', icon: Package, label: 'Kho & Đổi Trả' },
  { href: '/knowledge', icon: BookOpen, label: 'Knowledge' },
  { href: '/settings', icon: Settings, label: 'Settings' },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <nav className="sidebar-nav">
        <div className="sidebar-logo">
          <Zap size={20} color="white" />
        </div>

        {NAV_ITEMS.map(({ href, icon: Icon, label }) => (
          <Link key={href} href={href} title={label}>
            <div className={`nav-item ${pathname.startsWith(href) ? 'active' : ''}`}>
              <Icon size={20} />
            </div>
          </Link>
        ))}

        <div style={{ flex: 1 }} />
        <div className="nav-item" title="Thông báo">
          <Bell size={20} />
          <span className="badge" />
        </div>
      </nav>

      {/* Main content */}
      <main className="main-content">
        {children}
      </main>
    </div>
  );
}
