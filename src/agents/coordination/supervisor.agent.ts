import Agent from '@/types/agent.interface';
import { openai } from '@ai-sdk/openai';
import { generateText, tool } from 'ai';
import { z } from 'zod';
import { researcherAgent } from '../planning/researcher.agent';
import { plannerAgent } from '../planning/planner.agent';

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
        researcher: researcherAgent,
        planner: plannerAgent,
      },
      maxSteps: 5,
    });

    return text;
  }
}

const supervisorAgent = tool({
  description: 'A tool that runs the supervisor agent',
  parameters: z.object({
    prompt: z.string(),
  }),
  execute: async ({ prompt }) => {
    const text = await runSupervisor(prompt);
    return text;
  },
});

function runSupervisor(prompt: string) {
  return supervisorAgent.execute({ prompt });
}

export { supervisorAgent, runSupervisor };
