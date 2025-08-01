import React, { useCallback, useRef, useEffect } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  Connection,
  NodeChange,
  EdgeChange,
  OnConnect,
  OnNodesChange,
  OnEdgesChange,
  ReactFlowProvider
} from '@xyflow/react';
import { AgentNode } from './nodes/AgentNode';
import { WorkflowNode } from './nodes/WorkflowNode';
import { InputNode } from './nodes/InputNode';
import { OutputNode } from './nodes/OutputNode';
import { WorkflowNode as WorkflowNodeType, WorkflowEdge } from '@/types/execution/visual-workflow';
import { generateNodeId, getNextStepIndex } from '@/utils/workflowConverter';
import { useResizeObserverErrorHandler } from '@/hooks/useResizeObserverErrorHandler';

// Node types mapping
const nodeTypes = {
  agent: AgentNode,
  workflow: WorkflowNode,
  input: InputNode,
  output: OutputNode,
};

interface WorkflowCanvasProps {
  nodes: WorkflowNodeType[];
  edges: WorkflowEdge[];
  onNodesChange: (changes: NodeChange[]) => void;
  onEdgesChange: (changes: EdgeChange[]) => void;
  onConnect: (connection: Connection) => void;
  onWorkflowChange: (nodes: WorkflowNodeType[], edges: WorkflowEdge[]) => void;
}

export const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onWorkflowChange
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const workflowChangeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Handle ResizeObserver errors
  useResizeObserverErrorHandler();

  // Debounced workflow change handler
  const debouncedWorkflowChange = useCallback((updatedNodes: WorkflowNodeType[], updatedEdges: WorkflowEdge[]) => {
    if (workflowChangeTimeoutRef.current) {
      clearTimeout(workflowChangeTimeoutRef.current);
    }
    
    workflowChangeTimeoutRef.current = setTimeout(() => {
      onWorkflowChange(updatedNodes, updatedEdges);
    }, 100); // 100ms debounce
  }, [onWorkflowChange]);

  // Handle node changes with debouncing
  const handleNodesChange: OnNodesChange = useCallback(
    (changes) => {
      onNodesChange(changes);
      
      // Only update workflow for position changes to reduce unnecessary updates
      const positionChanges = changes.filter(change => change.type === 'position') as Array<{
        type: 'position';
        id: string;
        position: { x: number; y: number };
      }>;
      
      if (positionChanges.length > 0) {
        const updatedNodes = nodes.map(node => {
          const positionChange = positionChanges.find(change => change.id === node.id);
          if (positionChange && positionChange.position) {
            return { ...node, position: positionChange.position };
          }
          return node;
        });
        
        debouncedWorkflowChange(updatedNodes, edges);
      }
    },
    [nodes, edges, onNodesChange, debouncedWorkflowChange]
  );

  // Handle edge changes
  const handleEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      onEdgesChange(changes);
      
      // Update workflow when edges change
      const updatedEdges = changes.reduce((acc, change) => {
        if (change.type === 'remove') {
          return acc.filter(edge => edge.id !== change.id);
        }
        return acc;
      }, edges as WorkflowEdge[]);
      
      debouncedWorkflowChange(nodes, updatedEdges);
    },
    [nodes, edges, onEdgesChange, debouncedWorkflowChange]
  );

  // Handle connections
  const handleConnect: OnConnect = useCallback(
    (connection) => {
      const newEdge: WorkflowEdge = {
        id: `edge-${connection.source}-${connection.target}`,
        source: connection.source!,
        target: connection.target!,
        type: 'default',
        data: {
          stepIndex: getNextStepIndex(nodes)
        }
      };
      
      onConnect(connection);
      onWorkflowChange(nodes, [...edges, newEdge]);
    },
    [nodes, edges, onConnect, onWorkflowChange]
  );

  // Handle drag and drop
  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();

      if (!reactFlowWrapper.current) return;

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const data = event.dataTransfer.getData('application/reactflow');

      if (!data) return;

      const { type, data: nodeData } = JSON.parse(data);
      const position = {
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      };

      const newNode: WorkflowNodeType = {
        id: generateNodeId(type),
        type: type as 'agent' | 'workflow' | 'input' | 'output',
        position,
        data: {
          name: nodeData.name,
          description: nodeData.description,
          agentId: type === 'agent' ? nodeData.name : undefined,
          workflowId: type === 'workflow' ? nodeData.name : undefined,
          stepIndex: type === 'agent' || type === 'workflow' ? getNextStepIndex(nodes) : undefined,
        },
      };

      const updatedNodes = [...nodes, newNode];
      onWorkflowChange(updatedNodes, edges);
    },
    [nodes, edges, onWorkflowChange]
  );

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (workflowChangeTimeoutRef.current) {
        clearTimeout(workflowChangeTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div className="w-full h-full" ref={reactFlowWrapper}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={handleNodesChange}
          onEdgesChange={handleEdgesChange}
          onConnect={handleConnect}
          onDragOver={onDragOver}
          onDrop={onDrop}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-left"
          className="bg-background"
          // Add performance optimizations
          minZoom={0.1}
          maxZoom={1.5}
          defaultViewport={{ x: 0, y: 0, zoom: 1 }}
          // Reduce unnecessary re-renders during drag
          onNodeDragStart={() => {}}
          onNodeDrag={() => {}}
          onNodeDragStop={() => {}}
        >
          <Background />
          <Controls />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}; 