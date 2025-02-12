import { AgentConfig } from "../config/agent-config.interface";

interface ToolOutput {
  toolName: string;
  output: any;
}

interface ToolDetails {
  name: string;
  description: string;
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
