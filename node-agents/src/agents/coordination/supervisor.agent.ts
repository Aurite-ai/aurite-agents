import Agent from "@/types/agent.interface";
import { openai } from "@ai-sdk/openai";
import { generateText, tool } from "ai";
import { z } from "zod";
import ExecutorAgent from "../execution/executor.agent";
import { PlannerAgent } from "../planning";

export default class SupervisorAgent extends Agent {
  async execute(instructions: string) {
    const plannerAgent = new PlannerAgent(this.config, this.stateManager);
    // const researcherAgent = new ResearcherAgent(this.config, this.stateManager);
    const executorAgent = new ExecutorAgent(this.config, this.stateManager);

    const { text } = await generateText({
      prompt: `
      You are a supervisor agent. Your job is to coordinate the work of other agents to accomplish a goal.
      You have access to planning tools and external agents to help you with this.

      It's important that you dont get stuck in circles - for example, most tasks only require a few steps to complete.

      Use the executor agent to interface with the tools and external agents to accomplish the task.

      ${instructions}`,
      model: openai(this.config.defaultModel),
      temperature: 0.2,
      onStepFinish: ({ text, toolResults }) =>
        this.addInternalMessage(text, toolResults),
      tools: {
        // researcher: researcherAgent.getTool(),
        planner: plannerAgent.getTool(),
        // directory: createAgentDirectoryTool((agents) =>
        //   this.addInternalMessage(`Found ${agents.length} agents`)
        // ),
        executorAgent: executorAgent.getTool(),
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
