import React from 'react';

interface LogoProps {
  className?: string;
}

export const Logo: React.FC<LogoProps> = ({ className = "w-10 h-10" }) => {
  return (
    <img
      src="/logo.png"
      alt="Agent Studio Logo"
      className={className}
    />
  );
};
