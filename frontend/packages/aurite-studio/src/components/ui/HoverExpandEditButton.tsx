import React from 'react';
import { FileText, Workflow, Edit } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface HoverExpandEditButtonProps {
  workflow: any;
  onEdit: (workflow: any, mode: 'text' | 'visual') => void;
  className?: string;
}

export default function HoverExpandEditButton({ 
  workflow, 
  onEdit, 
  className = '' 
}: HoverExpandEditButtonProps) {
  // For Custom Workflows, show a simple edit button (no dropdown)
  if (workflow.type === 'custom_workflow') {
    return (
      <Button
        variant="outline"
        size="sm"
        onClick={(e) => {
          e.stopPropagation();
          onEdit(workflow, 'text'); // Mode doesn't matter for custom workflows
        }}
        className={className}
      >
        <Edit className="h-4 w-4 mr-2" />
        Edit
      </Button>
    );
  }

  // For Linear Workflows, show the expandable dropdown with Text/Visual options
  return (
    <div className={`relative group ${className}`}>
      {/* Default State - Single Edit Button */}
      <Button
        variant="outline"
        size="sm"
        className="transition-all duration-200 ease-out"
      >
        <Edit className="h-4 w-4 mr-2" />
        Edit
      </Button>

      {/* Dropdown State - Vertical Options (appears above button to avoid clipping) */}
      <div className="absolute bottom-full left-0 mb-1 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 ease-out z-[9999]">
        <div className="bg-popover border border-border rounded-lg shadow-lg py-1 min-w-[140px] whitespace-nowrap">
          {/* Text Edit Option */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit(workflow, 'text');
            }}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors text-left"
          >
            <FileText className="h-4 w-4" />
            <span>Text</span>
          </button>

          {/* Visual Edit Option */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEdit(workflow, 'visual');
            }}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent hover:text-accent-foreground transition-colors text-left"
          >
            <Workflow className="h-4 w-4" />
            <span>Visual</span>
          </button>
        </div>
      </div>
    </div>
  );
}
