import { createPlaywrightTool } from "./tools";

describe("PlaywrightTool", () => {
  it("should be able to run", async () => {
    const playwrightTool = createPlaywrightTool();

    const result = await playwrightTool.execute(
      {
        objective: "Extract the main content of the page",
        url: "https://www.cbsnews.com/us/",
      },
      {
        toolCallId: "1",
        messages: [],
      }
    );

    console.log(result);
    expect(result).toBeDefined();
  }, 20000);
});
