import {
  McpServer,
  ResourceTemplate,
} from "@modelcontextprotocol/sdk/server/mcp.js";
import axios from "axios";
import { JSONSchema } from "openai/lib/jsonschema";
import { z } from "zod";

interface SmitheryServerListResult {
  qualifiedName: string;
  displayName: string;
  description: string;
  // Link to Smithery server page
  homepage: string;
  // Number of times the server has been used via tool calling
  useCount: string;
  // True if this server is deployed on Smithery as a WebSocket server
  isDeployed: boolean;
  createdAt: string;
}

interface SmitheryServer {
  qualifiedName: string;
  displayName: string;
  deploymentUrl: string;
  connections: Array<{
    type: string;
    url?: string;
    configSchema: JSONSchema;
  }>;
}

interface SmitherySearchResults {
  servers: Array<SmitheryServerListResult>;
  pagination: {
    currentPage: number;
    pageSize: number;
    totalPages: number;
    totalCount: number;
  };
}

// Create an MCP server
const server = new McpServer({
  name: "Demo",
  version: "1.0.0",
});

server.tool(
  "search",
  { query: z.string(), page: z.number().default(1) },
  async ({ query }) => {
    try {
      const { data } = await axios.get<SmitherySearchResults>(
        `https://registry.smithery.ai/servers`,
        {
          params: {
            q: query,
          },
        }
      );

      return {
        content: [
          {
            type: "text",
            text: `Servers found: ${data.servers
              .map(
                (s) =>
                  `${s.displayName} (${s.qualifiedName}) - ${s.description}`
              )
              .join(", ")}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error fetching servers: ${error}`,
          },
        ],
      };
    }
  }
);

// Add a dynamic greeting resource
server.resource(
  "greeting",
  new ResourceTemplate("greeting://{name}", { list: undefined }),
  async (uri, { name }) => ({
    contents: [
      {
        uri: uri.href,
        text: `Hello, ${name}!`,
      },
    ],
  })
);

export { server as metaServer };
