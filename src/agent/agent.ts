import { generateId, ToolResult, ToolResultPart } from "ai";
import { AgentConfig } from "./config/agent-config.interface";
import StateManager from "./modules/state/state-manager";

export default class Agent {
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
