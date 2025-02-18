import { z } from "zod";

export interface ExternalAgent {
  id: string;
  name: string;
  description: string;
  platform: string;
  endpoint: string;
  inputSchema: object;
}

export async function getAgents(query: string) {
  const crewAiAgents: ExternalAgent[] = getCrewAiAgents(query);
  const swarmsAgents: ExternalAgent[] = getSwarmsAgents(query);

  return [...crewAiAgents, ...swarmsAgents];
}

export async function getAgent({ agentId }: { agentId: string }) {
  const agents = await getAgents(agentId);
  return agents.find((agent) => agent.id === agentId);
}

export async function executeAgent({
  agent,
  input,
}: {
  agent: ExternalAgent;
  input: any;
}) {
  // mock function to simulate calling an external agent

  return {
    jobId: "123",
    jobStatus: "in-progress",
    message: `Called ${agent.name} with input ${JSON.stringify(input)}`,
    result: "success",
  };
}

export async function checkAgentStatus({ jobId }: { jobId: string }) {
  // mock function to simulate checking the status of an external agent

  const agent = {
    name: "crew-ai-email-assistant",
  };

  return {
    jobId,
    jobStatus: "completed",
    message: `Status of ${agent.name} with jobId ${jobId}`,
    result: "success",
  };
}

function getCrewAiAgents(query: string): ExternalAgent[] {
  return [
    {
      id: "crew-ai-email-assistant",
      name: "crew-ai-email-assistant",
      description: "An AI assistant for email management.",
      platform: "crew-ai",
      endpoint: `https://api.crew.ai/v1/agents?query=${query}`,
      inputSchema: {
        type: "object",
        properties: {
          email: { type: "string" },
          task: { type: "string" },
        },
        required: ["email", "task"],
      },
    },
  ];
}
function getSwarmsAgents(query: string): ExternalAgent[] {
  return [];
}
