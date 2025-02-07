import Agent from "@/agent/agent";
import { openai } from "@ai-sdk/openai";
import { generateText } from "ai";

export default class PlannerAgent extends Agent {
  async execute(instructions: string) {
    const stateManager = this.stateManager;

    const { text } = await generateText({
      prompt: `You are a planner agent. Your job is not to solve a problem, but create a good plan for other agents to accomplish it. Return a detailed plan for these instructions: ${instructions}`,
      onStepFinish: ({ text }) => this.addInternalMessage(text),
      model: openai("o3-mini"),
      temperature: 0.2,
    });

    stateManager.handleUpdate({
      type: "plan",
      payload: text,
    });

    return text;
  }
}
