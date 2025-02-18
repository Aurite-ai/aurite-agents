import Agent from "@/types/agent.interface";
import { openai } from "@ai-sdk/openai";
import { generateText, tool } from "ai";
import { z } from "zod";
import StateManager from "@/context/state-manager";
import ResearcherAgent from "./researcher.agent";

export default class PlannerAgent extends Agent {
  async execute(instructions: string) {
    const stateManager = this.stateManager;

    const researcherAgent = new ResearcherAgent(this.config, this.stateManager);

    const { text } = await generateText({
      prompt: `You are a planner agent. Your job is not to solve a problem, but create a good plan for other agents to accomplish it. Return a detailed plan for these instructions: ${instructions}`,
      onStepFinish: ({ text }) => this.addInternalMessage(text),
      model: openai(this.config.defaultModel),
      temperature: 0.2,
      tools: {
        researcher: researcherAgent.getTool(),
      },
    });

    stateManager.handleUpdate({
      type: "plan",
      payload: text,
    });

    return text;
  }

  getTool(opts: any = {}) {
    return tool({
      description: "A tool that runs the planner agent",
      parameters: z.object({
        prompt: z.string(),
      }),
      execute: async ({ prompt }) => {
        return this.execute(prompt);
      },
    });
  }
}

export { PlannerAgent };
