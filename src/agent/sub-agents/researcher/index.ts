import { openai } from "@ai-sdk/openai";
import { generateText } from "ai";
import { TavilySearchTool } from "./tools";

export default async function runResearcher(prompt: string) {
  const { text } = await generateText({
    prompt: prompt,
    model: openai("o3-mini"),
    temperature: 0.2,
    tools: {
      webSearch: TavilySearchTool,
    },
    maxSteps: 4,
  });

  return text;
}
