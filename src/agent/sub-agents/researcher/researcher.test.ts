import { AgentConfig } from "@/agent/config/agent-config.interface";
import ResearchAgent from "./agent";
import StateManager from "@/agent/modules/state/state-manager";

const fs = require("fs");

describe("Researcher", () => {
  it("should be able to run", async () => {
    const config: AgentConfig = {
      name: "test-researcher",
      description: "test researcher",
      defaultModel: "3o-mini",
    };

    const state = new StateManager({
      references: [],
    });

    const researcher = new ResearchAgent(config, state);

    const text = await researcher.execute(
      "What is your prediction for the 2025 superbowl winner? Output your answer as markdown."
    );

    // write to file for debugging
    fs.writeFileSync("tests/agent-outputs/researcher-test.md", text);

    fs.writeFileSync(
      "tests/agent-outputs/researcher-state.json",
      JSON.stringify(state.getState(), null, 2)
    );

    expect(text).toBeDefined();
  }, 100000);
});
