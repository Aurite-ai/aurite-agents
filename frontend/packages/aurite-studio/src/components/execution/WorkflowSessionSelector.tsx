import React from 'react';
import { GenericSessionSelector, BaseSessionInfo } from './GenericSessionSelector';
import { WorkflowSessionSelectorProps } from '@/types/execution';

// Workflow-specific session interface extending the base
interface WorkflowSessionInfo extends BaseSessionInfo {
  workflow_name: string;
  step_count: number;
  current_step?: number;
}

export const WorkflowSessionSelector: React.FC<WorkflowSessionSelectorProps> = ({
  workflowName,
  selectedSessionId,
  onSessionSelect,
  onSessionCreate,
  disabled = false
}) => {
  // Mock sessions for now - this will be replaced with actual session data
  const mockSessions: WorkflowSessionInfo[] = [
    {
      id: 'workflow-session-1',
      name: 'Data Processing Pipeline',
      workflow_name: workflowName,
      step_count: 3,
      current_step: 2,
      last_activity: new Date(Date.now() - 1000 * 60 * 45), // 45 minutes ago
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
      status: 'active'
    },
    {
      id: 'workflow-session-2', 
      name: 'Customer Analysis Flow',
      workflow_name: workflowName,
      step_count: 5,
      current_step: 5,
      last_activity: new Date(Date.now() - 1000 * 60 * 60 * 3), // 3 hours ago
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1 day ago
      status: 'active'
    }
  ];

  // Format metadata for workflow sessions
  const formatWorkflowSessionMetadata = (session: WorkflowSessionInfo): string => {
    if (session.current_step !== undefined) {
      return `${session.current_step}/${session.step_count} steps`;
    }
    return `${session.step_count} steps`;
  };

  return (
    <GenericSessionSelector
      entityName="workflow"
      selectedSessionId={selectedSessionId}
      onSessionSelect={onSessionSelect}
      onSessionCreate={onSessionCreate}
      sessions={mockSessions}
      formatSessionMetadata={formatWorkflowSessionMetadata}
      disabled={disabled}
    />
  );
};
