import React from 'react';
import { useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  
  // Determine if we're on the home page for layout adjustments
  const isHomePage = location.pathname === '/';

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-auto">
        {/* Header */}
        <Header />

        {/* Main Content Area */}
        <main className={`flex-1 overflow-auto ${isHomePage ? 'flex items-center justify-center' : 'flex flex-col'} px-6 ${isHomePage ? 'pb-8' : 'pt-12 pb-8'}`}>
          {children}
        </main>
      </div>
    </div>
  );
}
