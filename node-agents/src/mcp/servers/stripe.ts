import { StripeAgentToolkit } from "@stripe/agent-toolkit/modelcontextprotocol";

const dotenv = require("dotenv");

console.log("Loading environment variables from .env file");

dotenv.config({ path: ".env" });

const stripeServer = new StripeAgentToolkit({
  secretKey: process.env.STRIPE_SECRET_KEY!,
  configuration: {
    actions: {
      paymentLinks: {
        create: true,
      },
      products: {
        create: true,
      },
      prices: {
        create: true,
      },
    },
  },
});

export { stripeServer };

// async function main() {
//   const transport = new StdioServerTransport();
//   await stripeServer.connect(transport);
//   console.error("Stripe MCP Server running on stdio");
// }

// main().catch((error) => {
//   console.error("Fatal error in main():", error);
//   process.exit(1);
// });
