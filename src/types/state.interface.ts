import { CoreMessage, ToolResultPart } from 'ai';

interface StateUpdate {
  type: string;
  payload: any;
}

interface InternalMessage {
  agentName: string;
  agentId: string;
  message: string;
  toolResults: ToolResultPart[];
  createdAt: Date;
}

interface BaseState {
  status: string;
  messages: CoreMessage[];
  internalMessages: InternalMessage[];
}

export { StateUpdate, InternalMessage, BaseState };
