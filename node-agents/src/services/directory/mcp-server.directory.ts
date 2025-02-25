import { validateApiKeys } from "@/lib/env-checker";
import { createSmitheryUrl, MultiClient } from "@smithery/sdk";

import {
  StdioClientTransport,
  StdioServerParameters,
} from "@modelcontextprotocol/sdk/client/stdio.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory";
import { stripeServer } from "@/mcp/servers";
import { WebSocketClientTransport } from "@modelcontextprotocol/sdk/client/websocket";
Object.assign(global, { WebSocket: require("ws") });

type MCPServer = (
  | StdioServerParameters
  | {
      url: string;
    }
) & {
  name: string;
  type: "npx" | "local" | "websocket";
};

const API_KEYS = {
  META_MCP: process.env.METAMCP_API_KEY,
};

validateApiKeys(API_KEYS);

const MCP_SERVERS: Array<MCPServer> = [
  {
    name: "sequential-thinking",
    url: "wss://server.smithery.ai/@smithery-ai/server-sequential-thinking/ws",
    type: "websocket",
  },
  {
    name: "memory-server",
    command: "npx",
    args: ["-y", "@modelcontextprotocol/server-memory"],
    type: "npx",
  },
  {
    name: "metamcp",
    command: "npx",
    args: ["-y", "@metamcp/mcp-server-metamcp"],
    env: {
      METAMCP_API_KEY: API_KEYS.META_MCP,
    },
    type: "npx",
  },
  {
    name: "taskmanager",
    command: "npx",
    args: ["-y", "@kazuph/mcp-taskmanager"],
    type: "npx",
  },
  {
    name: "web-research",
    command: "npx",
    args: ["-y", "@mzxrai/mcp-webresearch"],
    type: "npx",
  },
];

const convertToStdioServerParameters = (
  server: StdioServerParameters
): StdioServerParameters => {
  // if server.command is not npx, return the server as is
  if (server.command !== "npx") {
    return server;
  }
  return {
    ...server,
    command: "cmd",
    args: ["/C", `npx -y ${server.command} ${server.args?.join(" ") || ""}`],
  };
};

export const getMcpTransorts = (filter?: string[]) => {
  const [clientTransport, serverTransport] =
    InMemoryTransport.createLinkedPair();

  stripeServer.connect(serverTransport);

  // convert to object with name as key and StdioServerParameters as value
  return MCP_SERVERS.filter(
    (server) => !filter || filter.includes(server.name)
  ).reduce(
    (acc, server) => {
      acc[server.name] = getTransport(server);
      return acc;
    },
    {
      stripe: clientTransport,
    } as Record<
      string,
      StdioClientTransport | InMemoryTransport | WebSocketClientTransport
    >
  );
};

export const getTransport = (
  server: MCPServer
): WebSocketClientTransport | StdioClientTransport | undefined => {
  if (server.type === "websocket" && "url" in server) {
    return new WebSocketClientTransport(createSmitheryUrl(server.url));
  }
  if (server.type === "npx" && "command" in server) {
    return new StdioClientTransport(convertToStdioServerParameters(server));
  }
  // Adding a default return to handle the "local" type case
  return undefined;
};

// export const loadMcpServerTools = async (serverName: string) => {
//   const server = MCP_SERVERS.find((server) => server.name === serverName);
//   if (!server) {
//     throw new Error(`Server ${serverName} not found`);
//   }
//   const transport = new StdioClientTransport(
//     convertToStdioServerParameters(server)
//   );

//   const client = new MultiClient({
//     name: "Smithery SDK Test Client",
//     version: "1.0.0",
//   });

//   await client.connectAll({
//     [server.name]: transport,
//   });

//   // return the tools from the client
//   return client.listTools();
// };
