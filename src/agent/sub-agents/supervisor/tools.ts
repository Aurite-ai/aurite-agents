import { generateText, tool } from "ai";
import { z } from "zod";
import { openai } from "@ai-sdk/openai";

const researcherAgent = tool({
  description: "A tool that runs the researcher agent",
  parameters: z.object({
    prompt: z.string(),
  }),
  execute: async ({ prompt }) => {
    try {
      const text = await runResearcher(prompt);
      return text;
    } catch (error) {
      console.error("Error in researcherAgent:", error);
      return `Error: ${error}`;
    }
  },
});

export { researcherAgent };
function runResearcher(prompt: string) {
  throw new Error("Function not implemented.");
}
