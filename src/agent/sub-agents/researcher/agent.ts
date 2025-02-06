import Agent from "@/agent/agent";
import { openai } from "@ai-sdk/openai";
import { generateText } from "ai";
import { TavilySearchTool } from "./tools";

export default class ResearcherAgent extends Agent {
  async execute(instructions: string) {
    const stateManager = this.stateManager;

    const { text } = await generateText({
      prompt: instructions,
      model: openai("o3-mini"),
      temperature: 0.2,
      tools: {
        webSearch: TavilySearchTool,
      },
      maxSteps: 4,
    });

    return text;
  }
}
