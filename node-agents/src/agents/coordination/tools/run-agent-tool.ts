import { executeAgent, getAgent } from "@/services/directory/agent-directory";
import { tool } from "ai";
import { z } from "zod";

const runAgentTool = tool({
  description:
    "A tool that runs an agent. Only use when you have a toolId, granted from the agent directory tool.",
  parameters: z.object({
    agentId: z.string(),
    input: z.any(),
  }),
  async execute({ agentId, input }) {
    const agent = await getAgent({ agentId });
    const result = await executeAgent({ agent, input });
    return result;
  },
});

export { runAgentTool };
