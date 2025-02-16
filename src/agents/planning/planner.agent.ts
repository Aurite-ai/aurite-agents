import Agent from '@/types/agent.interface';
import { openai } from '@ai-sdk/openai';
import { generateText, tool } from 'ai';
import { z } from 'zod';
import { researcherAgent } from './researcher.agent';
import StateManager from '@/state/state-manager';

export default class PlannerAgent extends Agent {
  async execute(instructions: string) {
    const stateManager = this.stateManager;

    const { text } = await generateText({
      prompt: `You are a planner agent. Your job is not to solve a problem, but create a good plan for other agents to accomplish it. Return a detailed plan for these instructions: ${instructions}`,
      onStepFinish: ({ text }) => this.addInternalMessage(text),
      model: openai(this.config.defaultModel),
      temperature: 0.2,
      tools: {
        researcher: researcherAgent,
      },
    });

    stateManager.handleUpdate({
      type: 'plan',
      payload: text,
    });

    return text;
  }
}

const plannerAgent = tool({
  description: 'A tool that runs the planner agent',
  parameters: z.object({
    prompt: z.string(),
  }),
  execute: async ({ prompt }) => {
    return plannerAgent.execute({ prompt });
  },
});

export { plannerAgent };
