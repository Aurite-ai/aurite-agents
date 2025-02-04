import { generateText } from "ai";
import AgentOptions from "../../../interfaces/agent-options.interface";
import { openai } from "@ai-sdk/openai";
import { researcherTool } from "./tools";

export default async function runSupervisor(options: AgentOptions) {
  const { text } = await generateText({
    prompt: options.prompt,
    model: openai("gpt-4o"),
    temperature: 0.2,
    tools: {
      researcher: researcherTool,
    },
  });

  console.log(text);
  return text;
}
