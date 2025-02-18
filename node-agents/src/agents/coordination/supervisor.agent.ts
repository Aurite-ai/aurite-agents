import Agent from "@/types/agent.interface";
import { openai } from "@ai-sdk/openai";
import { generateText, tool } from "ai";
import { z } from "zod";
import { PlannerAgent, ResearcherAgent } from "../planning";
import { createAgentDirectoryTool } from "./tools/agent-directory-tool";
import { runAgentTool } from "./tools/run-agent-tool";

export default class SupervisorAgent extends Agent {
  async execute(instructions: string) {
    const plannerAgent = new PlannerAgent(this.config, this.stateManager);
    // const researcherAgent = new ResearcherAgent(this.config, this.stateManager);

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
        // researcher: researcherAgent.getTool(),
        planner: plannerAgent.getTool(),
        directory: createAgentDirectoryTool((agents) =>
          this.addInternalMessage(`Found ${agents.length} agents`)
        ),
        runAgent: runAgentTool,
      },
      maxSteps: 5,
    });

    return text;
  }
  getTool(opts: any = {}) {
    return tool({
      description: "A tool that runs the supervisor agent",
      parameters: z.object({
        prompt: z.string(),
      }),
      execute: async ({ prompt }) => {
        return this.execute(prompt);
      },
    });
  }
}

export { SupervisorAgent };
