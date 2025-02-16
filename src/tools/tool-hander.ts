import { tool } from 'ai';
import { z } from 'zod';
import { defaultToolSchema } from '@/types/tool.interface';
import StateManager from '@/state/state-manager';
import pickAgent from '@/routes/agent.router';
import { ToolOutput, ToolDetails } from '@/types/tool.interface';
import { Agent, AgentConfig } from '@/types/agent.interface';
const agentNames = ['researcher', 'evaluator', 'planner'] as const;

interface CreateCallAgentTool {
  name: (typeof agentNames)[number];
  config: AgentConfig;
  stateManager: StateManager<any>;
}

export async function sendOutput(toolOutput: ToolOutput, config: AgentConfig) {
  console.log(
    `Sending output from ${toolOutput.toolName} to ${config.name}:`,
    toolOutput.output
  );

  return toolOutput.output;
}

export function handleAgentError(
  error: Error,
  toolDetails: ToolDetails,
  config: AgentConfig
) {
  console.error(`Error in ${toolDetails.name}:`, error);
  return sendOutput(
    { toolName: toolDetails.name, output: `Error: ${error.message}` },
    config
  );
}

export function createAgentTool(options: CreateCallAgentTool) {
  return tool({
    description: 'Call an sub-agent to perform a specific task.',
    parameters: defaultToolSchema.extend({
      instructions: z.string().describe('The instructions for the agent.'),
    }),
    execute: async (params: { instructions: string }) => {
      const { instructions } = params;

      try {
        const Agent = pickAgent(options.name);

        // Initialize the agent with the provided config and state manager
        const agent = new Agent(options.config, options.stateManager);

        console.log(
          `Executing agent ${options.name} with instructions:`,
          instructions
        );

        // Call the agent's method with the provided instructions
        const output = await agent.execute(instructions);

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
            description: 'Call an agent to perform a specific task.',
          },
          options.config
        );
      }
    },
  });
}
