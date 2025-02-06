import { AgentConfig } from "./config/agent-config.interface";
import StateManager from "./modules/state/state-manager";

export default class Agent {
  constructor(
    protected config: AgentConfig,
    protected stateManager: StateManager<any>
  ) {}

  private getStateManager() {
    return this.stateManager;
  }
}
