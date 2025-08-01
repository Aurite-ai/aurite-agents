import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { motion } from 'framer-motion';

interface InputNodeData {
  name: string;
  description?: string;
  config?: any;
  agentId?: string;
  workflowId?: string;
  stepIndex?: number;
}

const InputNodeComponent: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeData = data as unknown as InputNodeData;
  
  return (
    <motion.div
      className={`
        relative bg-card border-2 rounded-lg p-4 min-w-[140px] shadow-sm
        ${selected ? 'border-green-500 shadow-md' : 'border-green-300'}
        hover:shadow-md transition-all duration-200
      `}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Node Content */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
          <span className="text-lg">📥</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-foreground truncate">
            {nodeData.name}
          </div>
          <div className="text-xs text-muted-foreground">
            Input
          </div>
        </div>
      </div>
      
      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-green-500 border-2 border-background"
      />
      
      {/* Selection Indicator */}
      {selected && (
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full" />
      )}
    </motion.div>
  );
};

// Memoize the component to prevent unnecessary re-renders
export const InputNode = memo(InputNodeComponent); 