import { AgentConfig } from "@/types/agent.interface";
import SupervisorAgent from "../../src/agents/coordination/supervisor.agent";
import StateManager from "@/context/state-manager";

const fs = require("fs");

describe("Supervisor tool route test", () => {
  it("should be able to run", async () => {
    const config: AgentConfig = {
      name: "test-supervisor",
      description: "test supervisor",
      defaultModel: "gpt-4o",
    };

    const state = new StateManager({
      status: "idle",
      messages: [],
      internalMessages: [],
    });

    const supervisor = new SupervisorAgent(config, state);

    const text = await supervisor.execute(
      "Send an email to patrick@test.com about in the form of a poem about snakes. Do not ask to confirm."
    );

    // write to file for debugging
    fs.writeFileSync("tests/fixtures/agent-outputs/supervisor-test.md", text);

    fs.writeFileSync(
      "tests/fixtures/agent-outputs/supervisor-state.json",
      JSON.stringify(state.getState(), null, 2)
    );

    expect(text).toBeDefined();
  }, 100000);
});
