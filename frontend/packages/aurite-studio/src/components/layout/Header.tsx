import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from '@/contexts/ThemeContext';

export default function Header() {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="absolute top-4 right-4 z-10">
      <Button
        variant="ghost"
        size="icon"
        onClick={toggleTheme}
        className="w-9 h-9 rounded-lg"
      >
        {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </Button>
    </header>
  );
}
