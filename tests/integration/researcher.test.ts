import { AgentConfig } from "@/types/agent.interface";
import ResearchAgent from "../../src/agents/planning/researcher.agent";
import StateManager from "@/context/state-manager";

const fs = require("fs");

describe("Researcher", () => {
  it("should be able to run", async () => {
    const config: AgentConfig = {
      name: "test-researcher",
      description: "test researcher",
      defaultModel: "3o-mini",
    };

    const state = new StateManager({
      status: "idle",
      messages: [],
      internalMessages: [],
    });

    const researcher = new ResearchAgent(config, state);

    const text = await researcher.execute(
      "What is your prediction for the 2025 superbowl winner? Output your answer as markdown."
    );

    // write to file for debugging
    fs.writeFileSync("tests/fixtures/agent-outputs/researcher-test.md", text);

    fs.writeFileSync(
      "tests/fixtures/agent-outputs/researcher-state.json",
      JSON.stringify(state.getState(), null, 2)
    );

    expect(text).toBeDefined();
  }, 100000);
});
