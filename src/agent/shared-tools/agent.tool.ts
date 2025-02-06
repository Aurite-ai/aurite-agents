import { tool } from "ai";
import { z } from "zod";
import { defaultToolSchema } from "./tool-default";
import { AgentConfig } from "../config/agent-config.interface";
import StateManager from "../modules/state/state-manager";
import Agent from "../agent";
import { handleAgentError, sendOutput } from "./tool-utils";
import ResearcherAgent from "../sub-agents/researcher/agent";

const agentNames = ["researcher", "evaluator", "planner"] as const;

interface CreateCallAgentTool {
  name: (typeof agentNames)[number];
  config: AgentConfig;
  stateManager: StateManager<any>;
}

export function createAgentTool(options: CreateCallAgentTool) {
  return tool({
    description: "Call an sub-agent to perform a specific task.",
    parameters: defaultToolSchema.extend({
      instructions: z.string().describe("The instructions for the agent."),
    }),
    execute: async (params: { instructions: string }) => {
      const { instructions } = params;

      try {
        // Initialize the agent with the provided config and state manager
        const agent = new ResearcherAgent(options.config, options.stateManager);

        // Call the agent's method with the provided instructions
        const output = await agent[options.name].execute(instructions);

        // Send the output using the provided config
        return sendOutput(
          { toolName: `Create Agent Tool[${options.name}]`, output },
          options.config
        );
      } catch (error) {
        // Handle any errors that occur during the agent call
        return handleAgentError(
          error as Error,
          {
            name: `Create Agent Tool[${options.name}]`,
            description: "Call an agent to perform a specific task.",
          },
          options.config
        );
      }
    },
  });
}
