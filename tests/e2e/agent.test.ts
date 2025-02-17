import StateManager from "@/context/state-manager";
import Agent from "@/types/agent.interface";
import { describe, it } from "node:test";

describe("Agent", () => {
  it("should run the agent", async () => {
    const agent = new Agent(
      {
        name: "test-agent",
        description: "test agent",
        defaultModel: "3o-mini",
      },
      new StateManager({
        status: "idle",
        messages: [],
        internalMessages: [],
      })
    );
    const result = await agent.addInternalMessage(
      "What is the capital of France?"
    );
    expect(result).toBe("Paris");
  });
});
