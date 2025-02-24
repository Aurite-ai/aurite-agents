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
