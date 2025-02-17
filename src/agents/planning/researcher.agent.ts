import Agent from "@/types/agent.interface";
import { openai } from "@ai-sdk/openai";
import { generateText, tool } from "ai";
import { createPlaywrightTool, createTavilySearchTool } from "@/tools/search";
import { z } from "zod";

export default class ResearcherAgent extends Agent {
  async execute(instructions: string) {
    const stateManager = this.stateManager;

    const { text } = await generateText({
      prompt: `You are a deep researcher.
      Use the web search tool to find relevant sources, and use the web page scraper to extract information from the sources you find.

      Avoid at all costs non-information such as "The spectrum of topics highlights the wide-ranging nature of U.S. news" which has no relevant insights. Be as specific as possible. Do not return information outside of the sources you research.

      Be discriminating in the sources you decide to pursue further. Not all sources will be relevant.

      Make sure your research is up to date. The current date is ${new Date().toLocaleDateString(
        "en-US",
        {
          year: "numeric",
          month: "long",
          day: "numeric",
        }
      )}.

      --- OBJECTIVE ---
      Perform searches and research to accomplish this: ${instructions}`,
      model: openai("o3-mini"),
      temperature: 0.2,
      onStepFinish: ({ text, toolResults }) =>
        this.addInternalMessage(text, toolResults),
      tools: {
        webSearch: createTavilySearchTool({
          onFindResults: (references) => {
            stateManager.add("references", [
              ...(stateManager.get("references") ?? []),
              ...references,
            ]);
            return `I found ${references.length} results.`;
          },
        }),
        webPageScraper: createPlaywrightTool(),
      },
      maxSteps: 5,
    });

    return text;
  }

  getTool(opts: any = {}) {
    return tool({
      description: "A tool that runs the research agent",
      parameters: z.object({
        prompt: z.string(),
      }),
      execute: async ({ prompt }) => {
        return this.execute(prompt);
      },
    });
  }
}

export { ResearcherAgent };
