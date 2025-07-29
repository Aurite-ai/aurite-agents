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

// Base session interface that all session types must extend
export interface BaseSessionInfo {
  id: string;
  name: string;
  last_activity: Date;
  created_at: Date;
  status: 'active' | 'archived';
}

// Generic props interface
export interface GenericSessionSelectorProps<T extends BaseSessionInfo> {
  entityName: string; // "agent" or "workflow"
  selectedSessionId?: string | null;
  onSessionSelect: (sessionId: string | null) => void;
  onSessionCreate: (sessionName: string) => void;
  sessions?: T[];
  formatSessionMetadata: (session: T) => string; // Custom formatter for metadata display
  disabled?: boolean;
  isLoading?: boolean;
}

export function GenericSessionSelector<T extends BaseSessionInfo>({
  entityName,
  selectedSessionId,
  onSessionSelect,
  onSessionCreate,
  sessions = [],
  formatSessionMetadata,
  disabled = false,
  isLoading = false
}: GenericSessionSelectorProps<T>) {
  const [showNewSession, setShowNewSession] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');

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
            disabled={disabled || isLoading}
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
              
              {sessions.length > 0 && (
                <>
                  <div className="px-2 py-1.5 text-xs font-medium text-muted-foreground border-b">
                    Previous sessions
                  </div>
                  {sessions.map((session) => (
                    <SelectItem key={session.id} value={session.id}>
                      <div className="flex flex-col gap-1">
                        <span className="text-sm font-medium">{session.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {formatSessionMetadata(session)} • {formatLastActivity(session.last_activity)}
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
            disabled={disabled || isLoading}
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              onClick={handleCreateSession}
              disabled={!newSessionName.trim() || disabled || isLoading}
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
              disabled={disabled || isLoading}
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
      
      {isLoading && (
        <div className="text-xs text-muted-foreground">
          Loading sessions...
        </div>
      )}
    </div>
  );
}
