var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/services/mcp/server.ts
var server_exports = {};
__export(server_exports, {
  server: () => server,
  serverTransport: () => transport
});
module.exports = __toCommonJS(server_exports);
var import_mcp = require("@modelcontextprotocol/sdk/server/mcp.js");
var import_stdio = require("@modelcontextprotocol/sdk/server/stdio.js");
var import_zod = require("zod");
var server = new import_mcp.McpServer({
  name: "Echo",
  version: "1.0.0"
});
server.resource(
  "echo",
  new import_mcp.ResourceTemplate("echo://{message}", { list: void 0 }),
  async (uri, { message }) => ({
    contents: [
      {
        uri: uri.href,
        text: `Resource echo: ${message}`
      }
    ]
  })
);
server.tool("echo", { message: import_zod.z.string() }, async ({ message }) => ({
  content: [{ type: "text", text: `Tool echo: ${message}` }]
}));
var transport = new import_stdio.StdioServerTransport();
async function main() {
  await server.connect(transport);
  console.log("Connected to client");
}
main();
// Annotate the CommonJS export names for ESM import in node:
0 && (module.exports = {
  server,
  serverTransport
});
