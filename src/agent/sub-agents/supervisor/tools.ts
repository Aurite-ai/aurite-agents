import { generateText, tool } from "ai";
import { z } from "zod";
import { openai } from "@ai-sdk/openai";

const researcherTool = tool({
  description: "A tool that runs the researcher agent",
  parameters: z.object({
    prompt: z.string(),
  }),
  execute: async ({ prompt }) => {
    try {
    } catch (error) {}
    const { text } = await generateText({
      prompt: prompt,
      model: openai("o3-mini"),
      temperature: 0.2,
    });

    return text;
  },
});

export { researcherTool };
