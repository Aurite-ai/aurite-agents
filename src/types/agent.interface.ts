import { generateId, tool, ToolResult, ToolResultPart } from "ai";
import StateManager from "../context/state-manager";
import { z } from "zod";
import Logger from "@/lib/logger";

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

  async execute(input: string): Promise<any> {
    return input;
  }

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
