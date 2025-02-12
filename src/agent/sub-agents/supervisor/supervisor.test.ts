import { AgentConfig } from "@/agent/config/agent-config.interface";
import SupervisorAgent from "./agent";
import StateManager from "@/agent/modules/state/state-manager";

const fs = require("fs");

describe("Supervisor", () => {
  it("should be able to run", async () => {
    const config: AgentConfig = {
      name: "test-supervisor",
      description: "test supervisor",
      defaultModel: "gpt-4o",
    };

    const state = new StateManager({
      references: [],
    });

    const supervisor = new SupervisorAgent(config, state);

    const text = await supervisor.execute(
      "Who won the 2025 superbowl and how? Output your answer as markdown."
    );

    // write to file for debugging
    fs.writeFileSync("tests/agent-outputs/supervisor-test.md", text);

    fs.writeFileSync(
      "tests/agent-outputs/supervisor-state.json",
      JSON.stringify(state.getState(), null, 2)
    );

    expect(text).toBeDefined();
  }, 100000);
});
