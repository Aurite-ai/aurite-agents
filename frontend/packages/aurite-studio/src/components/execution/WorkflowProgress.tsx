import React from 'react';
import { CheckCircle, XCircle, Loader2, Circle, MinusCircle } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { WorkflowProgressProps } from '@/types/execution';

export const WorkflowProgress: React.FC<WorkflowProgressProps> = ({ 
  steps, 
  currentStepIndex, 
  completedSteps, 
  currentStepProgress = 0,
  startTime 
}) => {
  const getStepStatus = (stepIndex: number) => {
    const completedStep = completedSteps.find(s => s.stepIndex === stepIndex);
    if (completedStep) return completedStep.status;
    if (stepIndex === currentStepIndex) return 'executing';
    if (stepIndex < currentStepIndex) return 'completed';
    return 'pending';
  };

  const getStepIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'executing':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'skipped':
        return <MinusCircle className="h-4 w-4 text-yellow-500" />;
      default:
        return <Circle className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const overallProgress = currentStepIndex >= 0 
    ? ((currentStepIndex + (currentStepProgress / 100)) / steps.length) * 100
    : 0;

  return (
    <div className="space-y-4">
      {/* Overall Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium">
            Step {Math.max(0, currentStepIndex + 1)} of {steps.length}
          </span>
          <span className="text-muted-foreground">
            {Math.round(overallProgress)}% complete
          </span>
        </div>
        <div className="w-full bg-muted rounded-full h-2">
          <div 
            className="bg-primary h-2 rounded-full transition-all duration-300"
            style={{ width: `${overallProgress}%` }}
          />
        </div>
      </div>

      {/* Step Timeline */}
      <div className="space-y-2">
        {steps.map((step, index) => {
          const stepName = typeof step === 'string' ? step : step.name;
          const status = getStepStatus(index);
          const completedStep = completedSteps.find(s => s.stepIndex === index);
          
          return (
            <div 
              key={index}
              className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${
                status === 'executing' ? 'bg-blue-50 dark:bg-blue-900/20' : ''
              }`}
            >
              {getStepIcon(status)}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-medium truncate ${
                    status === 'executing' ? 'text-blue-700 dark:text-blue-300' : ''
                  }`}>
                    {stepName}
                  </span>
                  {completedStep?.endTime && completedStep?.startTime && (
                    <span className="text-xs text-muted-foreground">
                      {Math.round((completedStep.endTime.getTime() - completedStep.startTime.getTime()) / 1000)}s
                    </span>
                  )}
                </div>
                {status === 'executing' && currentStepProgress > 0 && (
                  <div className="mt-1">
                    <div className="w-full bg-muted rounded-full h-1">
                      <div 
                        className="bg-blue-500 h-1 rounded-full transition-all duration-300"
                        style={{ width: `${currentStepProgress}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Timing Information */}
      {startTime && (
        <div className="text-xs text-muted-foreground text-center">
          Started {formatDistanceToNow(startTime, { addSuffix: true })}
        </div>
      )}
    </div>
  );
};
