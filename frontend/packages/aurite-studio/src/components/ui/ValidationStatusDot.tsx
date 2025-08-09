import React from 'react';

interface ValidationStatusDotProps {
  isValidated: boolean;
  className?: string;
}

export const ValidationStatusDot: React.FC<ValidationStatusDotProps> = ({
  isValidated,
  className = '',
}) => {
  const dotColor = isValidated ? 'bg-green-500' : 'bg-orange-500';

  return <div className={`w-2 h-2 rounded-full ${dotColor} ${className}`} />;
};

export default ValidationStatusDot;
