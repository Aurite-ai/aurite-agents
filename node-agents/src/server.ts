import express from "express";
import { chatRouter } from "./routes";
import { runClient } from "./services/smithery";
import { agentRouter } from "./routes/agent.router";

const app = express();

app.use(express.json());

// create middleware to log requests that were recieved
app.use(
  (req: express.Request, res: express.Response, next: express.NextFunction) => {
    console.log(`${req.method} ${req.path}`);
    console.log(req.body);
    next();
  }
);

app.get("/", (req, res) => {
  res.send("Server is running!");
});

app.use("/v1/chat", chatRouter);
app.use("/v1/agent", agentRouter);

app.use("/test", async (req, res): Promise<any> => {
  await runClient();
  res.send("Smithery client is running!");
});

const port = 4444;

app.listen(port, () => {
  console.log(`Server is running at http://localhost:${port}`);
});
