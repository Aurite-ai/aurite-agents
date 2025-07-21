import React from 'react';
import { Clock } from 'lucide-react';
import { ExecutionProgressProps } from '@/types/execution';

export const ExecutionProgress: React.FC<ExecutionProgressProps> = ({
  progress,
  currentStep,
  startTime,
  estimatedDuration
}) => {
  const formatElapsedTime = (startTime?: Date): string => {
    if (!startTime) return '0s';
    
    const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000);
    if (elapsed < 60) {
      return `${elapsed}s`;
    } else {
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      return `${minutes}m ${seconds}s`;
    }
  };

  return (
    <div className="space-y-3">
      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Progress</span>
          <span className="font-medium">{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-muted rounded-full h-2">
          <div 
            className="bg-primary h-2 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      </div>

      {/* Status and Timing */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          <span>{formatElapsedTime(startTime)} elapsed</span>
        </div>
        {currentStep && (
          <span className="text-right">{currentStep}</span>
        )}
      </div>
    </div>
  );
};
