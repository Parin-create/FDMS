import { useState, type ReactNode } from 'react';

import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { env } from '@/config/env';

interface RootLayoutProps {
  children: ReactNode;
}

/** Authenticated application shell: sidebar + header + scrollable content. */
export function RootLayout({ children }: RootLayoutProps): JSX.Element {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex min-h-screen flex-col md:pl-64">
        <Header onMenuClick={() => setSidebarOpen(true)} />

        <main className="flex-1 px-4 py-8 md:px-8">
          <div className="mx-auto max-w-6xl">{children}</div>
        </main>

        <footer className="border-t border-gray-200 bg-white">
          <div className="mx-auto max-w-6xl px-4 py-4 text-xs text-gray-500 md:px-8">
            {env.appName} · File Sharing &amp; Document Management System
          </div>
        </footer>
      </div>
    </div>
  );
}
