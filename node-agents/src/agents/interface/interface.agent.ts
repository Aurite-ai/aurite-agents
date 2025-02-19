import Agent from "@/types/agent.interface";
import { openai } from "@ai-sdk/openai";
import { generateText, tool } from "ai";
import { z } from "zod";
import { PlannerAgent, ResearcherAgent } from "../planning";
import { createAgentDirectoryTool } from "../coordination/tools/agent-directory.tool";
import { runAgentTool } from "../coordination/tools/run-agent.tool";
import { userConfirmTool } from "./tools/user-confirm.tool";
import { stdin } from "node:process";

export default class SupervisorAgent extends Agent {
  async execute(instructions: string) {
    const plannerAgent = new PlannerAgent(this.config, this.stateManager);
    // const researcherAgent = new ResearcherAgent(this.config, this.stateManager);

    const { text, toolCalls } = await generateText({
      prompt: `
     You are an interface agent - your job is to interact with the user, render UI tools and return their results.

     Your instructions from the supervisor agent are: ${instructions}.
     `,
      model: openai(this.config.defaultModel),
      temperature: 0.2,
      onStepFinish: ({ text, toolResults }) =>
        this.addInternalMessage(text, toolResults),
      tools: {
        interface: userConfirmTool,
      },
      maxSteps: 2,
    });

    if (toolCalls) {
      const toolCall = toolCalls[0];

      if (toolCall.toolName === "interface") {
        //TODO:  perform some action that prompts the user
      }
    }

    return text;
  }
  getTool(opts: any = {}) {
    return tool({
      description:
        "A tool that runs the interface agent. Useful for getting human-in-the-loop feedback.",
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
