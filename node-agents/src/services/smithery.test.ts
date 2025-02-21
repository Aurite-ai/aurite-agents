import { runClient } from "./smithery";

describe("Smithery", () => {
  it("should be able to create a new Smithery", async () => {
    await runClient();
  });
});
