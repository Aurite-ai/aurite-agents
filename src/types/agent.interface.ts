import { generateId, ToolResult, ToolResultPart } from 'ai';
import StateManager from '../state/state-manager';

interface SubAgentConfig {}

interface AgentConfig {
  name: string;
  description: string;
  defaultModel: string;
}

interface AgentOptions {
  prompt: string;
}
class Agent {
  constructor(
    protected config: AgentConfig,
    protected stateManager: StateManager<any>,
    protected id: string = generateId()
  ) {}

  addInternalMessage(message: string, toolResults: ToolResultPart[] = []) {
    this.stateManager.addInternalMessage({
      message,
      toolResults,
      agentId: this.id,
      agentName: this.constructor.name,
      createdAt: new Date(),
    });
  }

  getStateManager() {
    return this.stateManager;
  }
}

export { Agent, AgentOptions, AgentConfig, SubAgentConfig };
export default Agent;
