import express from "express";
import chatRouter from "./routes/chat";

const app = express();

app.use(express.json());

app.get("/", (req, res) => {
  res.send("Server is running!");
});

app.use("/v1/chat", chatRouter);

const port = 4444;

app.listen(port, () => {
  console.log(`Server is running at http://localhost:${port}`);
});
