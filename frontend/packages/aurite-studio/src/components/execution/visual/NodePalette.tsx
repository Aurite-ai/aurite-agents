import React, { useEffect, useMemo } from 'react';

interface NodePaletteProps {
  availableAgents: any[];
  availableWorkflows: any[];
  onNodeDrag: (nodeType: string, nodeData: any) => void;
}

// Custom comparison function for React.memo
const areNodePalettePropsEqual = (prevProps: NodePaletteProps, nextProps: NodePaletteProps) => {
  // Compare arrays by length and content
  if (prevProps.availableAgents.length !== nextProps.availableAgents.length) return false;
  if (prevProps.availableWorkflows.length !== nextProps.availableWorkflows.length) return false;
  
  // For now, just compare lengths to avoid deep comparison overhead
  // In a production app, you might want to implement proper deep comparison
  return true;
};

const NodePaletteComponent: React.FC<NodePaletteProps> = ({
  availableAgents,
  availableWorkflows,
  onNodeDrag
}) => {
  // Memoize the console logs to prevent them from running on every render
  useEffect(() => {
    console.log('NodePalette - availableAgents:', availableAgents);
    console.log('NodePalette - availableWorkflows:', availableWorkflows);
  }, [availableAgents, availableWorkflows]);

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>, nodeType: string, nodeData: any) => {
    e.dataTransfer.setData('application/reactflow', JSON.stringify({
      type: nodeType,
      data: nodeData
    }));
    e.dataTransfer.effectAllowed = 'move';
    onNodeDrag(nodeType, nodeData);
  };

  // Helper function to get a safe key
  const getSafeKey = (item: any, index: number): string => {
    if (typeof item.name === 'string') {
      return item.name;
    } else if (item.name && typeof item.name === 'object' && item.name.name) {
      return item.name.name;
    } else if (item.id) {
      return item.id;
    } else {
      return `item-${index}`;
    }
  };

  // Helper function to get display name
  const getDisplayName = (item: any): string => {
    if (typeof item.name === 'string') {
      return item.name;
    } else if (item.name && typeof item.name === 'object' && item.name.name) {
      return item.name.name;
    } else {
      return 'Unknown';
    }
  };

  // Memoize the agents and workflows to prevent unnecessary re-renders
  const memoizedAgents = useMemo(() => availableAgents, [availableAgents]);
  const memoizedWorkflows = useMemo(() => availableWorkflows, [availableWorkflows]);

  return (
    <div className="bg-card border border-border rounded-lg p-4 space-y-4">
      <h3 className="font-medium text-foreground text-sm">Available Components</h3>
      
      {/* Agents Section */}
      <div className="space-y-2">
        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Agents ({memoizedAgents.length})
        </h4>
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {memoizedAgents.map((agent, index) => (
            <div
              key={getSafeKey(agent, index)}
              draggable
              onDragStart={(e: React.DragEvent<HTMLDivElement>) => handleDragStart(e, 'agent', agent)}
              className="
                flex items-center gap-3 p-2 rounded-md border border-border
                bg-background hover:bg-muted cursor-grab active:cursor-grabbing
                transition-colors duration-200
              "
            >
              <div className="w-6 h-6 bg-primary/10 rounded-full flex items-center justify-center">
                <span className="text-xs">🤖</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-foreground truncate">
                  {getDisplayName(agent)}
                </div>
                {agent.description && (
                  <div className="text-xs text-muted-foreground truncate">
                    {agent.description}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Workflows Section */}
      <div className="space-y-2">
        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Workflows ({memoizedWorkflows.length})
        </h4>
        <div className="space-y-2 max-h-40 overflow-y-auto">
          {memoizedWorkflows.map((workflow, index) => (
            <div
              key={getSafeKey(workflow, index)}
              draggable
              onDragStart={(e: React.DragEvent<HTMLDivElement>) => handleDragStart(e, 'workflow', workflow)}
              className="
                flex items-center gap-3 p-2 rounded-md border border-border
                bg-background hover:bg-muted cursor-grab active:cursor-grabbing
                transition-colors duration-200
              "
            >
              <div className="w-6 h-6 bg-secondary/10 rounded-full flex items-center justify-center">
                <span className="text-xs">🔄</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-foreground truncate">
                  {getDisplayName(workflow)}
                </div>
                {workflow.description && (
                  <div className="text-xs text-muted-foreground truncate">
                    {workflow.description}
                  </div>
                )}
                <div className="text-xs text-muted-foreground">
                  {workflow.steps?.length || 0} steps
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Quick Add Section */}
      <div className="space-y-2">
        <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Quick Add
        </h4>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => onNodeDrag('input', { name: 'Input' })}
            className="
              p-2 rounded-md border border-green-300 bg-green-50
              hover:bg-green-100 transition-colors duration-200
              text-xs font-medium text-green-700
            "
          >
            📥 Input
          </button>
          <button
            onClick={() => onNodeDrag('output', { name: 'Output' })}
            className="
              p-2 rounded-md border border-blue-300 bg-blue-50
              hover:bg-blue-100 transition-colors duration-200
              text-xs font-medium text-blue-700
            "
          >
            📤 Output
          </button>
        </div>
      </div>
    </div>
  );
};

// Export the memoized component
export const NodePalette = React.memo(NodePaletteComponent, areNodePalettePropsEqual); 