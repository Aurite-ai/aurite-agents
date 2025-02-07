import Agent from "@/agent/agent";
import { openai } from "@ai-sdk/openai";
import { generateText } from "ai";
import { createTavilySearchTool } from "./tools";

export default class ResearcherAgent extends Agent {
  async execute(instructions: string) {
    const stateManager = this.stateManager;

    const { text } = await generateText({
      prompt: `You are a deep researcher. Perform searches and research to accomplish this: ${instructions}`,
      model: openai("o3-mini"),
      temperature: 0.2,
      onStepFinish: ({ text }) => this.addInternalMessage(text),
      tools: {
        webSearch: createTavilySearchTool({
          onFindResults: (references) => {
            stateManager.add("references", [
              ...(stateManager.get("references") ?? []),
            ]);
            return `I found ${references.length} results.`;
          },
        }),
      },
      maxSteps: 4,
    });

    return text;
  }
}
