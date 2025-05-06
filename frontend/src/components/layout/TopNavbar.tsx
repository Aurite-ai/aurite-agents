import React from 'react';

const TopNavbar: React.FC = () => {
  return (
    <nav className="bg-dracula-current-line text-dracula-foreground p-4 shadow-lg">
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-4">
          {/* Placeholder for Company Logo */}
          <div className="w-8 h-8 bg-dracula-purple rounded-full flex items-center justify-center text-dracula-background font-bold">
            A
          </div>
          <h1 className="text-xl font-semibold text-dracula-foreground">Aurite AI Studio</h1>
        </div>
        <div className="flex items-center space-x-4">
          {/* Placeholder for User Profile Icon */}
          <div className="w-8 h-8 bg-dracula-comment bg-opacity-50 rounded-full flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-dracula-foreground">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
            </svg>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default TopNavbar;
