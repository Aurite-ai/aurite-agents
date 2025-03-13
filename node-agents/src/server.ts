import express from "express";
import { chatRouter } from "./routes/index.js";
import { runClient } from "./services/smithery.js";
import { agentRouter } from "./routes/agent.router.js";

const app = express();

app.use(express.json());

// create middleware to log requests that were received
app.use(
  (
    req: express.Request,
    _res: express.Response,
    next: express.NextFunction
  ) => {
    console.log(`${req.method} ${req.path}`);
    console.log(req.body);
    next();
  }
);

app.get("/", (_req, res) => {
  res.send("Server is running!");
});

app.use("/v1/chat", chatRouter);
app.use("/v1/agent", agentRouter);

app.use("/test", async (_req, res): Promise<any> => {
  await runClient();
  res.send("Smithery client is running!");
});

const port = 4444;

app.listen(port, () => {
  console.log(`Server is running at http://localhost:${port}`);
});
