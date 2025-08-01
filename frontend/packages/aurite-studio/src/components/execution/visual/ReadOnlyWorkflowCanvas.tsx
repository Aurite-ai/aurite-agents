import React, { useCallback, useRef, useEffect } from 'react';
import {
  ReactFlow,
  Controls,
  Background,
  ReactFlowProvider
} from '@xyflow/react';
import { AgentNode } from './nodes/AgentNode';
import { WorkflowNode } from './nodes/WorkflowNode';
import { InputNode } from './nodes/InputNode';
import { OutputNode } from './nodes/OutputNode';
import { WorkflowNode as WorkflowNodeType, WorkflowEdge } from '@/types/execution/visual-workflow';
import { useResizeObserverErrorHandler } from '@/hooks/useResizeObserverErrorHandler';

// Node types mapping
const nodeTypes = {
  agent: AgentNode,
  workflow: WorkflowNode,
  input: InputNode,
  output: OutputNode,
};

interface ReadOnlyWorkflowCanvasProps {
  nodes: WorkflowNodeType[];
  edges: WorkflowEdge[];
}

export const ReadOnlyWorkflowCanvas: React.FC<ReadOnlyWorkflowCanvasProps> = ({
  nodes,
  edges
}) => {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);

  // Handle ResizeObserver errors
  useResizeObserverErrorHandler();

  return (
    <div className="w-full h-full" ref={reactFlowWrapper}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          attributionPosition="bottom-left"
          className="bg-background"
          // Read-only settings
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnDrag={true}
          zoomOnScroll={true}
          zoomOnPinch={true}
          // Performance optimizations
          minZoom={0.1}
          maxZoom={1.5}
          defaultViewport={{ x: 0, y: 0, zoom: 1 }}
          // Disable all interactive features
          onNodeDragStart={() => {}}
          onNodeDrag={() => {}}
          onNodeDragStop={() => {}}
          onConnect={() => {}}
          onNodesChange={() => {}}
          onEdgesChange={() => {}}
        >
          <Background />
          <Controls />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}; 