import React from 'react';
import { Button } from '@/components/ui/button';
import { Edit3, Layout } from 'lucide-react';
import { WorkflowMode } from '@/types/execution/visual-workflow';

interface WorkflowModeToggleProps {
  mode: WorkflowMode;
  onModeChange: (mode: WorkflowMode) => void;
  disabled?: boolean;
}

export const WorkflowModeToggle: React.FC<WorkflowModeToggleProps> = ({
  mode,
  onModeChange,
  disabled = false
}) => {
  return (
    <div className="flex items-center gap-2 p-2 bg-muted rounded-lg">
      <Button
        variant={mode === 'text' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onModeChange('text')}
        disabled={disabled}
        className="flex items-center gap-2"
      >
        <Edit3 className="h-4 w-4" />
        <span className="hidden sm:inline">Text Mode</span>
      </Button>
      
      <Button
        variant={mode === 'visual' ? 'default' : 'ghost'}
        size="sm"
        onClick={() => onModeChange('visual')}
        disabled={disabled}
        className="flex items-center gap-2"
      >
        <Layout className="h-4 w-4" />
        <span className="hidden sm:inline">Visual Mode</span>
      </Button>
    </div>
  );
}; 