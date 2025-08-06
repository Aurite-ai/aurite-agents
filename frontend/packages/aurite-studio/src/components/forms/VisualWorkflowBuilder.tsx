import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Loader2, X, Settings, ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import {
  ReactFlow,
  Node,
  Edge,

  useNodesState,
  useEdgesState,
  Connection,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
  NodeTypes,
  EdgeTypes,
  Handle,
  Position,
  MarkerType,
  ConnectionMode,
  ConnectionLineType,
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
  EdgeProps,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAgentsWithConfigs } from '@/hooks/useAgents';
import { useCreateWorkflow, useUpdateWorkflow, useWorkflowConfigByName } from '@/hooks/useWorkflows';
import { useLLMs } from '@/hooks/useLLMs';
import mcpServersService from '@/services/mcpServers.service';
import agentsService from '@/services/agents.service';
import AgentPalette from './visual/AgentPalette';
import AgentConfigModal from './visual/AgentConfigModal';
import { AgentConfig } from '@/types/api.generated';

// Custom styles for dark theme controls
const controlsStyle = `
  .react-flow__controls {
    background: hsl(var(--card)) !important;
    border: 1px solid hsl(var(--border)) !important;
    border-radius: 8px !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    padding: 4px !important;
  }
  
  .react-flow__controls-button {
    background: hsl(var(--background)) !important;
    border: 1px solid hsl(var(--border)) !important;
    border-radius: 6px !important;
    color: hsl(var(--foreground)) !important;
    width: 32px !important;
    height: 32px !important;
    margin: 2px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
  }
  
  .react-flow__controls-button:hover {
    background: hsl(var(--muted)) !important;
    border-color: hsl(var(--primary)) !important;
    transform: scale(1.05) !important;
  }
  
  .react-flow__controls-button svg {
    fill: hsl(var(--foreground)) !important;
    stroke: hsl(var(--foreground)) !important;
    width: 16px !important;
    height: 16px !important;
  }
  
  .react-flow__controls-button:disabled {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
  }
  
  .react-flow__minimap {
    background: hsl(var(--card)) !important;
    border: 1px solid hsl(var(--border)) !important;
    border-radius: 8px !important;
  }
  
  .react-flow__minimap-mask {
    fill: hsl(var(--primary) / 0.2) !important;
    stroke: hsl(var(--primary)) !important;
    stroke-width: 2px !important;
  }
  
  .react-flow__minimap-node {
    fill: hsl(var(--muted-foreground)) !important;
  }
`;

interface VisualWorkflowBuilderProps {
  editMode?: boolean;
}

// Custom node type for agents
const AgentNode = ({ data, id }: { data: any; id: string }) => {
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (data?.onDelete && typeof data.onDelete === 'function') {
      data.onDelete(id);
    }
  };

  const handleConfig = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (data?.onConfig && typeof data.onConfig === 'function') {
      data.onConfig(id);
    }
  };

  const isConfigured = data?.agentConfig && (
    // Check for meaningful configuration beyond just type and name
    data.agentConfig.system_prompt || 
    data.agentConfig.description || 
    data.agentConfig.llm_config_id || 
    data.agentConfig.model ||
    (data.agentConfig.mcp_servers && data.agentConfig.mcp_servers.length > 0) ||
    (data.agentConfig.exclude_components && data.agentConfig.exclude_components.length > 0) ||
    data.agentConfig.include_history !== undefined ||
    data.agentConfig.auto !== undefined ||
    data.agentConfig.max_iterations !== undefined ||
    data.agentConfig.temperature !== undefined ||
    data.agentConfig.max_tokens !== undefined
  );


  return (
    <motion.div 
      className="relative group min-w-[150px] max-w-[280px] p-3"
      initial={{ scale: 0.95, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      {/* Main Node Card */}
      <div className="bg-card border border-border rounded-xl p-3 shadow-lg hover:shadow-xl transition-shadow duration-300 backdrop-blur-sm bg-opacity-95 relative overflow-visible">
        
        {/* Gradient Accent Bar */}
        <div className={`absolute top-0 left-0 right-0 h-1 ${isConfigured ? 'bg-gradient-to-r from-primary to-blue-500' : 'bg-gradient-to-r from-muted to-muted-foreground/20'}`} />
        
        {/* Status Indicator */}
        <div className="absolute top-3 right-3 flex items-center gap-2">
          {isConfigured && (
            <div className="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse shadow-lg" title="Agent is configured" />
          )}
        </div>

        {/* Action Buttons */}
        <div className="absolute -top-2 -right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-300 z-20">
          <button
            onClick={handleConfig}
            className={`w-6 h-6 ${
              isConfigured 
                ? 'bg-primary hover:bg-primary/80 text-primary-foreground' 
                : 'bg-muted hover:bg-muted/80 text-muted-foreground'
            } rounded-full flex items-center justify-center transition-all duration-200 shadow-md border border-white/20 hover:scale-110`}
            title={isConfigured ? "Agent is configured - click to edit" : "Configure agent"}
          >
            <Settings className="h-3 w-3" />
          </button>
          <button
            onClick={handleDelete}
            className="w-6 h-6 bg-destructive hover:bg-destructive/80 text-destructive-foreground rounded-full flex items-center justify-center transition-all duration-200 shadow-md border border-white/20 hover:scale-110"
            title="Delete agent"
          >
            <X className="h-3 w-3" />
          </button>
        </div>

        {/* Input Handle - Top */}
        <Handle
          type="target"
          position={Position.Top}
          className="w-5 h-5 bg-primary border-2 border-background hover:bg-primary/90 transition-colors duration-150 cursor-crosshair"
          style={{ 
            top: -10,
            borderRadius: '50%',
            boxShadow: '0 2px 8px rgba(99, 102, 241, 0.3)',
            zIndex: 10
          }}
          id="input"
        />
        
        {/* Node Icon and Header */}
        <div className="flex items-start gap-2 mb-2">
          <div className={`w-8 h-8 ${isConfigured ? 'bg-gradient-to-r from-primary to-blue-500' : 'bg-gradient-to-r from-muted to-muted-foreground/30'} rounded-lg flex items-center justify-center text-white shadow-md`}>
            <div className="w-4 h-4 bg-white/90 rounded-sm flex items-center justify-center">
              <div className="w-1.5 h-1.5 bg-current rounded-full" />
            </div>
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-foreground truncate">
              {data.label}
            </h3>
            <div className="text-xs text-muted-foreground mt-0.5">
              {data?.loading ? 'Loading...' : (isConfigured ? 'Configured' : 'Not configured')}
            </div>
          </div>
        </div>

        {/* Node Description */}
        {(data.description || data.agentConfig?.description) && (
          <div className="text-xs text-muted-foreground leading-relaxed line-clamp-2 mb-3">
            {data.agentConfig?.description || data.description}
          </div>
        )}

        {/* Configuration Details */}
        {isConfigured && data.agentConfig && (
          <div className="space-y-2">
            {data.agentConfig.llm_config && (
              <div className="flex items-center gap-2 text-xs">
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
                <span className="text-muted-foreground">LLM: {data.agentConfig.llm_config}</span>
              </div>
            )}
            {data.agentConfig.mcp_servers && data.agentConfig.mcp_servers.length > 0 && (
              <div className="flex items-center gap-2 text-xs">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <span className="text-muted-foreground">{data.agentConfig.mcp_servers.length} MCP Server{data.agentConfig.mcp_servers.length !== 1 ? 's' : ''}</span>
              </div>
            )}
          </div>
        )}

        {/* Output Handle - Bottom */}
        <Handle
          type="source"
          position={Position.Bottom}
          className="w-5 h-5 bg-primary border-2 border-background hover:bg-primary/90 transition-colors duration-150 cursor-crosshair"
          style={{ 
            bottom: -10,
            borderRadius: '50%',
            boxShadow: '0 2px 8px rgba(99, 102, 241, 0.3)',
            zIndex: 10
          }}
          id="output"
        />
      </div>
    </motion.div>
  );
};

// Custom edge with delete button
const CustomEdge = ({ 
  id, 
  sourceX, 
  sourceY, 
  targetX, 
  targetY, 
  sourcePosition, 
  targetPosition,
  style = {},
  markerEnd,
  data 
}: EdgeProps) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const handleDelete = () => {
    if (data?.onDelete && typeof data.onDelete === 'function') {
      data.onDelete(id);
    }
  };

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            fontSize: 12,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <button
            onClick={handleDelete}
            className="w-5 h-5 bg-destructive hover:bg-destructive/80 text-destructive-foreground rounded-full flex items-center justify-center shadow-md hover:scale-110 transition-all duration-200 opacity-0 hover:opacity-100 group-hover:opacity-100"
            title="Delete connection"
            style={{
              opacity: 0.7,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.opacity = '1';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = '0.7';
            }}
          >
            <X className="h-2.5 w-2.5" />
          </button>
        </div>
      </EdgeLabelRenderer>
    </>
  );
};

// Define custom node types
const nodeTypes: NodeTypes = {
  agentNode: AgentNode,
};

// Define custom edge types
const edgeTypes: EdgeTypes = {
  custom: CustomEdge,
};

// Custom Zoom Controls Component
const CustomZoomControls = () => {
  const { zoomIn, zoomOut, setViewport, getViewport } = useReactFlow();
  
  const handleZoomToLevel = (zoomLevel: number) => {
    const currentViewport = getViewport();
    setViewport({ 
      x: currentViewport.x, 
      y: currentViewport.y, 
      zoom: zoomLevel 
    }, { duration: 300 });
  };
  
  return (
    <div className="absolute bottom-6 right-6 z-10 bg-card border border-border rounded-lg shadow-lg p-2 flex flex-col gap-1">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleZoomToLevel(2.0)}
        className="text-xs h-8 w-16"
        title="Zoom to 200%"
      >
        200%
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleZoomToLevel(1.0)}
        className="text-xs h-8 w-16 bg-primary/20 border border-primary/30"
        title="Zoom to 100% (Default)"
      >
        100%★
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleZoomToLevel(0.5)}
        className="text-xs h-8 w-16"
        title="Zoom to 50%"
      >
        50%
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => handleZoomToLevel(0.25)}
        className="text-xs h-8 w-16"
        title="Zoom to 25%"
      >
        25%
      </Button>
    </div>
  );
};

export default function VisualWorkflowBuilder({ editMode = false }: VisualWorkflowBuilderProps): React.ReactElement {
  const navigate = useNavigate();
  const { name: workflowNameParam } = useParams<{ name: string }>();
  
  // Form state
  const [workflowName, setWorkflowName] = useState('');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [workflowFormPopulated, setWorkflowFormPopulated] = useState(false);
  
  // Agent configuration modal state
  const [configModalOpen, setConfigModalOpen] = useState(false);
  const [configModalNodeId, setConfigModalNodeId] = useState<string | null>(null);
  
  // Available configurations for dropdowns
  const [, setAvailableMCPServers] = useState<string[]>([]);
  
  // React Flow state
  const initialNodes: Node[] = [];
  const initialEdges: Edge[] = [];
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  
  // API Hooks
  const { data: agents = [], isLoading: agentsLoading } = useAgentsWithConfigs();
  const { data: llmConfigs = [] } = useLLMs();
  const createWorkflow = useCreateWorkflow();
  const updateWorkflow = useUpdateWorkflow();
  
  // Workflow-specific hooks for edit mode
  const { data: workflowConfig, isLoading: workflowConfigLoading } = useWorkflowConfigByName(
    workflowNameParam || '',
    !!workflowNameParam && editMode
  );

  // Handle edge deletion by ID
  const handleEdgeDelete = useCallback((edgeId: string) => {
    setEdges((eds) => eds.filter(edge => edge.id !== edgeId));
  }, [setEdges]);

  // Helper function to find a position that doesn't overlap with existing nodes
  const findAvailablePosition = useCallback((targetPosition: { x: number; y: number }) => {
    const nodeWidth = 280; // Approximate node width
    const nodeHeight = 120; // Approximate node height
    const minDistance = 50; // Minimum distance between nodes
    
    let bestPosition = { ...targetPosition };
    let attempts = 0;
    const maxAttempts = 20;
    
    while (attempts < maxAttempts) {
      let hasOverlap = false;
      
      // Check if current position overlaps with any existing node
      for (const node of nodes) {
        const dx = Math.abs(bestPosition.x - node.position.x);
        const dy = Math.abs(bestPosition.y - node.position.y);
        
        if (dx < nodeWidth + minDistance && dy < nodeHeight + minDistance) {
          hasOverlap = true;
          break;
        }
      }
      
      if (!hasOverlap) {
        break;
      }
      
      // Try a new position slightly offset
      bestPosition = {
        x: targetPosition.x + (attempts * 30),
        y: targetPosition.y + (attempts * 30),
      };
      attempts++;
    }
    
    return bestPosition;
  }, [nodes]);

  // Handle edge connections
  const onConnect = useCallback(
    (params: Connection) => {
      if (params.source && params.target) {
        const newEdge = {
          id: `edge-${params.source}-${params.target}-${Date.now()}`,
          source: params.source,
          target: params.target,
          sourceHandle: params.sourceHandle,
          targetHandle: params.targetHandle,
          type: 'custom',
          animated: true,
          style: { stroke: '#6366f1', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#6366f1',
          },
          data: {
            onDelete: handleEdgeDelete,
          },
        };
        
        setEdges((eds) => [...eds, newEdge]);
      }
    },
    [setEdges, handleEdgeDelete]
  );

  // Handle node deletion by ID
  const handleNodeDelete = useCallback((nodeId: string) => {
    // Remove the node
    setNodes((nds) => nds.filter(node => node.id !== nodeId));
    // Remove any edges connected to this node
    setEdges((eds) => eds.filter(edge => 
      edge.source !== nodeId && edge.target !== nodeId
    ));
  }, [setNodes, setEdges]);

  // Handle opening agent configuration
  const handleNodeConfig = useCallback((nodeId: string) => {
    setConfigModalNodeId(nodeId);
    setConfigModalOpen(true);
  }, []);

  // Handle saving agent configuration
  const handleConfigSave = useCallback((config: AgentConfig) => {
    if (configModalNodeId) {
      setNodes((nds) => 
        nds.map(node => 
          node.id === configModalNodeId 
            ? { 
                ...node, 
                data: { 
                  ...node.data, 
                  agentConfig: config,
                  // Update the label if the name changed
                  label: config.name || node.data.label,
                  agentName: config.name || node.data.agentName,
                }
              }
            : node
        )
      );
    }
    setConfigModalOpen(false);
    setConfigModalNodeId(null);
  }, [configModalNodeId, setNodes]);

  // Convert workflow steps to visual nodes and edges
  const convertStepsToVisual = useCallback(async (steps: string[], agentConfigurations?: Record<string, AgentConfig>) => {
    const newNodes: Node[] = [];
    const newEdges: Edge[] = [];
    
    // Create nodes and try to fetch configurations
    for (let index = 0; index < steps.length; index++) {
      const step = steps[index];
      let agentConfig = agentConfigurations?.[step];
      
      // If no embedded config, try to fetch from API
      if (!agentConfig) {
        try {
          agentConfig = await agentsService.getAgentConfig(step);
        } catch (error) {
          console.warn('⚠️ Failed to fetch agent config for edit mode:', step, error);
        }
      }
      
      // Create node for each step
      const node: Node = {
        id: `agent-${index}`,
        type: 'agentNode',
        position: { x: 300, y: 150 + (index * 200) }, // Vertical layout with better spacing
        data: {
          label: agentConfig?.name || step,
          agentName: step,
          onDelete: handleNodeDelete,
          onConfig: handleNodeConfig,
          // Include agent configuration if it exists
          ...(agentConfig && { agentConfig }),
          // Add debug info
          debugInfo: {
            stepName: step,
            hasEmbeddedConfig: !!agentConfigurations?.[step],
            hasFetchedConfig: !!agentConfig,
            configKeys: agentConfig ? Object.keys(agentConfig) : []
          }
        },
      };
      newNodes.push(node);
      
      // Create edge to connect to next step
      if (index < steps.length - 1) {
        const edge: Edge = {
          id: `edge-${index}`,
          source: `agent-${index}`,
          target: `agent-${index + 1}`,
          type: 'custom',
          animated: true,
          style: { stroke: '#6366f1', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#6366f1',
          },
          data: {
            onDelete: handleEdgeDelete,
          },
        };
        newEdges.push(edge);
      }
    }
    
    return { nodes: newNodes, edges: newEdges };
  }, [handleNodeDelete, handleNodeConfig, handleEdgeDelete]);

  // Effect to populate workflow form when workflow config is loaded
  useEffect(() => {
    const populateWorkflowForm = async () => {
      if (editMode && workflowConfig && workflowNameParam && !workflowFormPopulated) {
        // Populate form fields
        setWorkflowName(workflowConfig.name || '');
        setWorkflowDescription(workflowConfig.description || '');
        
        // Convert steps to visual representation
        if (workflowConfig.steps && Array.isArray(workflowConfig.steps)) {
          try {
            const { nodes: newNodes, edges: newEdges } = await convertStepsToVisual(
              workflowConfig.steps, 
              (workflowConfig as any).agent_configurations
            );
            setNodes(newNodes);
            setEdges(newEdges);
          } catch (error) {
            console.error('❌ Error converting steps to visual:', error);
          }
        }
        
        // Mark form as populated
        setWorkflowFormPopulated(true);
      } else if (!editMode && !workflowFormPopulated) {
        // Initialize form for create mode
        setWorkflowName('');
        setWorkflowDescription('');
        setNodes([]);
        setEdges([]);
        setWorkflowFormPopulated(true);
      }
    };

    populateWorkflowForm();
  }, [workflowConfig, workflowNameParam, editMode, workflowFormPopulated, convertStepsToVisual, setNodes, setEdges]);

  // Fetch MCP servers on component mount
  useEffect(() => {
    const fetchMCPServers = async () => {
      try {
        const servers = await mcpServersService.listMCPServers();
        setAvailableMCPServers(servers);
      } catch (error) {
        console.error('Failed to fetch MCP servers:', error);
        setAvailableMCPServers([]);
      }
    };

    fetchMCPServers();
  }, []);

  // Handle agent drop from palette
  const onAgentDrop = useCallback(async (agentName: string, position: { x: number; y: number }) => {
    // Find an available position that doesn't overlap
    const availablePosition = findAvailablePosition(position);
    
    // Create initial node without configuration
    const nodeId = `agent-${Date.now()}`;
    const initialNode: Node = {
      id: nodeId,
      type: 'agentNode',
      position: availablePosition,
      data: {
        label: agentName,
        agentName: agentName,
        onDelete: handleNodeDelete,
        onConfig: handleNodeConfig,
        loading: true, // Add loading state
      },
    };
    
    // Add the node immediately
    setNodes((nds) => [...nds, initialNode]);
    
    // Try to fetch the agent configuration
    try {
      const agentConfig = await agentsService.getAgentConfig(agentName);
      
      // Update the node with the configuration
      setNodes((nds) => 
        nds.map(node => 
          node.id === nodeId 
            ? {
                ...node,
                data: {
                  ...node.data,
                  agentConfig,
                  loading: false,
                }
              }
            : node
        )
      );
    } catch (error) {
      console.warn('Failed to fetch agent config for', agentName, ':', error);
      
      // Update node to remove loading state even if config fetch failed
      setNodes((nds) => 
        nds.map(node => 
          node.id === nodeId 
            ? {
                ...node,
                data: {
                  ...node.data,
                  loading: false,
                }
              }
            : node
        )
      );
    }
  }, [setNodes, handleNodeDelete, handleNodeConfig, findAvailablePosition]);

  // Handle node deletion
  const onNodesDelete = useCallback(
    (deletedNodes: Node[]) => {
      const deletedNodeIds = deletedNodes.map(node => node.id);
      // Also remove any edges connected to deleted nodes
      setEdges((eds) => eds.filter(edge => 
        !deletedNodeIds.includes(edge.source) && !deletedNodeIds.includes(edge.target)
      ));
    },
    [setEdges]
  );

  // Handle edge deletion
  const onEdgesDelete = useCallback(
    (deletedEdges: Edge[]) => {
      // Edges are automatically removed by React Flow
    },
    []
  );

  // Convert visual workflow to text workflow format
  const convertToWorkflowConfig = () => {
    // For now, create a simple sequential workflow from nodes
    // This is a basic implementation - can be enhanced for complex flows
    const steps = nodes.map(node => node.data?.agentName).filter(Boolean) as string[];
    
    // Extract agent configurations for agents that have been configured
    const agentConfigurations: Record<string, AgentConfig> = {};
    nodes.forEach(node => {
      const agentConfig = node.data?.agentConfig as AgentConfig;
      if (agentConfig && 
          node.data?.agentName && 
          typeof node.data.agentName === 'string' &&
          agentConfig.name) {
        agentConfigurations[node.data.agentName] = agentConfig;
      }
    });
    
    return {
      name: workflowName,
      type: "linear_workflow" as const,
      steps: steps,
      description: workflowDescription || undefined,
      // Include agent configurations if any exist
      ...(Object.keys(agentConfigurations).length > 0 && { agent_configurations: agentConfigurations })
    };
  };



  // Handle save workflow
  const handleSubmit = () => {
    if (!workflowName.trim() || nodes.length === 0) {
      return;
    }

    const workflowConfig = convertToWorkflowConfig();

    if (editMode && workflowNameParam) {
      // Edit mode - update existing workflow
      updateWorkflow.mutate({
        filename: workflowNameParam,
        config: workflowConfig
      }, {
        onSuccess: () => {
          navigate('/workflows');
        },
        onError: (error) => {
          console.error('❌ Failed to update visual workflow:', error);
        }
      });
    } else {
      // Create mode - create new workflow
      createWorkflow.mutate(workflowConfig, {
        onSuccess: () => {
          navigate('/workflows');
        },
        onError: (error) => {
          console.error('❌ Failed to create visual workflow:', error);
        }
      });
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Inject custom styles for controls */}
      <style dangerouslySetInnerHTML={{ __html: controlsStyle }} />
      
      {/* Left Sidebar - Agent Palette */}
      <AgentPalette 
        agents={agents}
        isLoading={agentsLoading}
        onAgentDrop={onAgentDrop}
      />

      {/* Main Canvas Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border bg-card">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/workflows')}
              className="w-9 h-9"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-2xl font-bold text-primary">
              {editMode ? 'Edit Visual Workflow' : 'Build New Visual Workflow'}
            </h1>
          </div>
          
          <div className="flex items-center gap-3">
            <Button 
              variant="outline"
              onClick={() => navigate('/workflows')}
            >
              Cancel
            </Button>
            <Button 
              className="px-6"
              onClick={handleSubmit}
              disabled={(createWorkflow.isPending || updateWorkflow.isPending) || !workflowName.trim() || nodes.length === 0}
            >
              {(createWorkflow.isPending || updateWorkflow.isPending) ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  {editMode ? 'Updating...' : 'Creating...'}
                </>
              ) : (
                editMode ? 'Update Visual Workflow' : 'Save Visual Workflow'
              )}
            </Button>
          </div>
        </div>

        {/* Workflow Details */}
        <div className="px-6 py-4 border-b border-border bg-card space-y-4">
          {/* Loading State for Workflow Config */}
          {workflowConfigLoading && editMode && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading workflow configuration...
            </div>
          )}
          
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="visual-workflow-name" className="text-sm font-medium text-foreground">
                Workflow Name
              </Label>
              <Input
                id="visual-workflow-name"
                placeholder="e.g., Visual Data Processing Workflow"
                value={workflowName}
                onChange={(e) => setWorkflowName(e.target.value)}
                className="text-base"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="visual-workflow-description" className="text-sm font-medium text-foreground">
                Description (Optional)
              </Label>
              <Input
                id="visual-workflow-description"
                placeholder="Brief description of the workflow"
                value={workflowDescription}
                onChange={(e) => setWorkflowDescription(e.target.value)}
                className="text-base"
              />
            </div>
          </div>
        </div>

        {/* Canvas */}
        <div 
          className="flex-1"
          onDrop={(e) => {
            e.preventDefault();
            const data = e.dataTransfer.getData('application/json');
            
            if (data) {
              try {
                const { agentName } = JSON.parse(data);
                const reactFlowBounds = document.querySelector('.react-flow')?.getBoundingClientRect();
                
                if (reactFlowBounds) {
                  const position = {
                    x: e.clientX - reactFlowBounds.left - 75, // Center the node
                    y: e.clientY - reactFlowBounds.top - 25,
                  };
                  onAgentDrop(agentName, position);
                }
              } catch (error) {
                console.error('Error parsing drag data:', error);
              }
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
          }}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodesDelete={onNodesDelete}
            onEdgesDelete={onEdgesDelete}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            defaultViewport={{ x: 0, y: 0, zoom: 1.0 }}
            fitViewOptions={{ padding: 0.3, minZoom: 0.05, maxZoom: 8.0 }}
            className="bg-background"
            defaultEdgeOptions={{
              type: 'smoothstep',
              animated: true,
              style: { stroke: '#6366f1', strokeWidth: 2 },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                color: '#6366f1',
              },
            }}
            connectionLineStyle={{ 
              stroke: '#6366f1', 
              strokeWidth: 3,
              strokeDasharray: '5,5',
              strokeLinecap: 'round'
            }}
            connectionMode={ConnectionMode.Strict}
            snapToGrid={true}
            snapGrid={[25, 25]}
            deleteKeyCode="Delete"
            multiSelectionKeyCode="Shift"
            selectNodesOnDrag={false}
            connectionRadius={25}
            connectionLineType={ConnectionLineType.SmoothStep}
          >
            <Controls />
            <MiniMap 
              nodeColor={(node) => '#6366f1'}
            />
            <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          </ReactFlow>
        </div>

        {/* Status Bar */}
        <div className="px-6 py-2 border-t border-border bg-card">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {nodes.length} agent{nodes.length !== 1 ? 's' : ''} • {edges.length} connection{edges.length !== 1 ? 's' : ''}
            </span>
            <span>
              {nodes.length === 0 
                ? "Drag agents from the left panel to create your workflow"
                : "Connect: drag from bottom blue circle to top blue circle of another agent • Delete: hover and click X"
              }
            </span>
          </div>
        </div>
      </div>

      {/* Agent Configuration Modal */}
      {configModalNodeId && (
        <AgentConfigModal
          isOpen={configModalOpen}
          onClose={() => {
            setConfigModalOpen(false);
            setConfigModalNodeId(null);
          }}
          onSave={handleConfigSave}
          agentName={String(nodes.find(node => node.id === configModalNodeId)?.data?.agentName || 'Agent')}
          initialConfig={nodes.find(node => node.id === configModalNodeId)?.data?.agentConfig || {}}
          availableLLMConfigs={llmConfigs}
        />
      )}
    </div>
  );
}