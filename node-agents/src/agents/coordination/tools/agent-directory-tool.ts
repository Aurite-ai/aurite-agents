import { getAgents } from "@/services/directory/agent-directory";
import { tool } from "ai";
import { z } from "zod";

const domains = [];

const createAgentDirectoryTool = (onResults: (results: any) => void) =>
  tool({
    description: "A tool that searches the agent directory for other agents.",
    parameters: z.object({
      query: z.string(),
      // TOOD: Expand this to include other params like domain, platform, etc.
    }),
    async execute({ query }) {
      const agents = await getAgents(query);
      onResults(agents);
      return agents;
    },
  });

export { createAgentDirectoryTool };
