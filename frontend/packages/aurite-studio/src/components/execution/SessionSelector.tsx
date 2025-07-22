import React, { useState } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { SessionSelectorProps } from '@/types/execution';

export const SessionSelector: React.FC<SessionSelectorProps> = ({
  agentName,
  selectedSessionId,
  onSessionSelect,
  onSessionCreate,
  disabled = false
}) => {
  const [showNewSession, setShowNewSession] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');

  // Mock sessions for now - this will be replaced with actual session data
  const mockSessions = [
    {
      id: 'session-1',
      name: 'Previous conversation',
      messageCount: 5,
      lastActivity: new Date(Date.now() - 1000 * 60 * 30) // 30 minutes ago
    },
    {
      id: 'session-2', 
      name: 'Weather discussion',
      messageCount: 12,
      lastActivity: new Date(Date.now() - 1000 * 60 * 60 * 2) // 2 hours ago
    }
  ];

  const handleCreateSession = () => {
    if (!newSessionName.trim()) return;
    
    onSessionCreate(newSessionName.trim());
    setNewSessionName('');
    setShowNewSession(false);
  };

  const formatLastActivity = (date: Date): string => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) {
      return `${diffMins}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else {
      return `${diffDays}d ago`;
    }
  };

  return (
    <div className="space-y-3">
      <Label className="text-sm font-medium text-foreground">Session</Label>
      
      {!showNewSession ? (
        <div className="space-y-2">
          <Select 
            value={selectedSessionId || 'new'} 
            onValueChange={(value) => {
              if (value === 'new') {
                onSessionSelect(null);
              } else if (value === 'create-new') {
                setShowNewSession(true);
              } else {
                onSessionSelect(value);
              }
            }}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select session..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="new">
                <div className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  New conversation
                </div>
              </SelectItem>
              
              {mockSessions.length > 0 && (
                <>
                  <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground border-b">
                    Previous sessions
                  </div>
                  {mockSessions.map((session) => (
                    <SelectItem key={session.id} value={session.id}>
                      <div className="flex flex-col gap-1">
                        <span className="text-sm font-medium">{session.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {session.messageCount} messages • {formatLastActivity(session.lastActivity)}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </>
              )}
              
              <SelectItem value="create-new">
                <div className="flex items-center gap-2 text-primary">
                  <Plus className="h-3 w-3" />
                  Create named session...
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      ) : (
        <div className="space-y-2">
          <Input
            placeholder="Enter session name..."
            value={newSessionName}
            onChange={(e) => setNewSessionName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleCreateSession();
              } else if (e.key === 'Escape') {
                setShowNewSession(false);
                setNewSessionName('');
              }
            }}
            autoFocus
            disabled={disabled}
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handleCreateSession}
              disabled={!newSessionName.trim() || disabled}
            >
              Create
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setShowNewSession(false);
                setNewSessionName('');
              }}
              disabled={disabled}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
      
      {selectedSessionId && (
        <div className="text-xs text-muted-foreground">
          Continuing conversation in existing session
        </div>
      )}
    </div>
  );
};
