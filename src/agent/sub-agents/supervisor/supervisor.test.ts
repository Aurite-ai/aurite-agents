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
      "Tell me about the canadian tarriff situation in Feb 2025. Output your final result in markdown format. First, use the planner to create a plan, then use the researcher(s) to execute the plan. Use the tools as needed. Be sure to use markdown for your final output."
    );

    // write to file for debugging
    fs.writeFileSync("supervisor-test.md", text);

    fs.writeFileSync(
      "supervisor-state.json",
      JSON.stringify(state.getState(), null, 2)
    );

    expect(text).toBeDefined();
  }, 100000);
});
