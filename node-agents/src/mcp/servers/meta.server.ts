import {
  getTransport,
  MCPServerObject,
} from "@/services/directory/mcp-server.directory.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { WebSocketClientTransport } from "@modelcontextprotocol/sdk/client/websocket.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
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
  connections: Array<{
    type: string;
    deploymentUrl?: string;
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

// TODO: convert this to a resource

function createMetaToolkit(config: {
  addServer: (
    name: string,
    transport: WebSocketClientTransport | StdioClientTransport
  ) => void;
}) {
  console.log("creating meta toolkit");
  const server = new McpServer({
    name: "Meta Toolkit",
    version: "1.0.0",
  });

  // Add a tool to the server

  server.tool(
    "search",
    { query: z.string(), page: z.number() },
    async ({ query, page }) => {
      try {
        console.log("searching for servers");
        const { data } = await axios.get<SmitherySearchResults>(
          `https://registry.smithery.ai/servers`,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${process.env.SMITHERY_API_KEY}`,
            },
            params: {
              q: query,
              page: page,
            },
          }
        );

        console.log("servers found", data.servers.slice(0, 3));

        return {
          content: [
            {
              type: "text",
              text: `Servers found: ${data.servers
                .map(
                  (s) =>
                    `${s.displayName} [${s.qualifiedName}] - ${s.description}`
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

  server.tool(
    "addServer",
    { serverName: z.string() },
    async ({ serverName }) => {
      console.log("adding server to toolset", serverName);

      const url = `https://registry.smithery.ai/servers/${serverName}`;
      console.log("url", url);

      try {
        const { data } = await axios.get<SmitheryServer>(url, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${process.env.SMITHERY_API_KEY}`,
          },
        });

        console.log("server found", data);

        const directory = transformToDirectory(data);

        console.log("directory", directory);

        const transport = getTransport(directory);

        config.addServer(serverName, transport);
        // implement this logic later
      } catch (error) {
        console.error("Error fetching server:", error);
        return {
          content: [
            {
              type: "text",
              text: `Error fetching server: ${error}`,
            },
          ],
        };
      }
      return {
        content: [
          {
            type: "text",
            text: `Server added: ${serverName}`,
          },
        ],
      };
    }
  );

  return server;
}

function transformToDirectory(server: SmitheryServer): MCPServerObject {
  if (server.connections.find((c) => c.type === "ws")) {
    const c = server.connections.find((c) => c.type === "ws");

    const url = c.deploymentUrl.replace("https://", "wss://") + "/ws";

    return {
      name: server.displayName,
      url,
      type: "websocket",
      config: {},
    };
  } else {
    return {
      name: server.displayName,
      command: "npx",
      args: ["-y", `@modelcontextprotocol/${server.qualifiedName}`],
      type: "npx",
      config: {},
    };
  }
}

export { createMetaToolkit, transformToDirectory };
