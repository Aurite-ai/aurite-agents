import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { motion } from 'framer-motion';

interface AgentNodeData {
  name: string;
  description?: string;
  config?: any;
  agentId?: string;
  workflowId?: string;
  stepIndex?: number;
}

const AgentNodeComponent: React.FC<NodeProps> = ({ data, selected }) => {
  const nodeData = data as unknown as AgentNodeData;
  
  return (
    <motion.div
      className={`
        relative bg-card border-2 rounded-lg p-4 min-w-[160px] shadow-sm
        ${selected ? 'border-primary shadow-md' : 'border-border'}
        hover:shadow-md transition-all duration-200
      `}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Input Handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-primary border-2 border-background"
      />
      
      {/* Node Content */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
          <span className="text-lg">🤖</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-foreground truncate">
            {nodeData.name}
          </div>
          <div className="text-xs text-muted-foreground">
            Agent
          </div>
          {nodeData.stepIndex && (
            <div className="text-xs text-primary font-medium mt-1">
              Step {nodeData.stepIndex}
            </div>
          )}
        </div>
      </div>
      
      {/* Output Handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-primary border-2 border-background"
      />
      
      {/* Selection Indicator */}
      {selected && (
        <div className="absolute -top-1 -right-1 w-3 h-3 bg-primary rounded-full" />
      )}
    </motion.div>
  );
};

// Memoize the component to prevent unnecessary re-renders
export const AgentNode = memo(AgentNodeComponent); 