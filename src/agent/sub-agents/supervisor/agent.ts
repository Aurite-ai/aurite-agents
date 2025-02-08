import Agent from "../../agent";
import { createAgentTool } from "@/agent/shared-tools/agent.tool";
import { openai } from "@ai-sdk/openai";
import { generateText } from "ai";

export default class SupervisorAgent extends Agent {
  async execute(instructions: string) {
    const stateManager = this.stateManager;

    const { text } = await generateText({
      prompt: `
      You are a supervisor agent. Your job is to coordinate the work of other agents to accomplish a goal.
      You have access to research and planning tools to help you with this.
      ${instructions}`,
      model: openai(this.config.defaultModel),
      temperature: 0.2,
      onStepFinish: ({ text, toolResults }) =>
        this.addInternalMessage(text, toolResults),
      tools: {
        researcher: createAgentTool({
          name: "researcher",
          config: this.config,
          stateManager,
        }),
        planner: createAgentTool({
          name: "planner",
          config: this.config,
          stateManager,
        }),
      },
      maxSteps: 5,
    });

    return text;
  }
}
