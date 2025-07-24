import React from 'react';
import { GenericSessionSelector, BaseSessionInfo } from './GenericSessionSelector';
import { SessionSelectorProps } from '@/types/execution';

// Agent-specific session interface extending the base
interface AgentSessionInfo extends BaseSessionInfo {
  agent_name: string;
  message_count: number;
}

export const SessionSelector: React.FC<SessionSelectorProps> = ({
  agentName,
  selectedSessionId,
  onSessionSelect,
  onSessionCreate,
  disabled = false
}) => {
  // Mock sessions for now - this will be replaced with actual session data
  const mockSessions: AgentSessionInfo[] = [
    {
      id: 'session-1',
      name: 'Previous conversation',
      agent_name: agentName,
      message_count: 5,
      last_activity: new Date(Date.now() - 1000 * 60 * 30), // 30 minutes ago
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 24), // 1 day ago
      status: 'active'
    },
    {
      id: 'session-2', 
      name: 'Weather discussion',
      agent_name: agentName,
      message_count: 12,
      last_activity: new Date(Date.now() - 1000 * 60 * 60 * 2), // 2 hours ago
      created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2), // 2 days ago
      status: 'active'
    }
  ];

  // Format metadata for agent sessions
  const formatAgentSessionMetadata = (session: AgentSessionInfo): string => {
    return `${session.message_count} messages`;
  };

  return (
    <GenericSessionSelector
      entityName="agent"
      selectedSessionId={selectedSessionId}
      onSessionSelect={onSessionSelect}
      onSessionCreate={onSessionCreate}
      sessions={mockSessions}
      formatSessionMetadata={formatAgentSessionMetadata}
      disabled={disabled}
    />
  );
};
