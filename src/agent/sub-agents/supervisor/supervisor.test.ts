import runSupervisor from ".";

describe("Supervisor", () => {
  it("should be able to run", async () => {
    const text = await runSupervisor({
      prompt: "Give me an overview of the 2025 tariff situation with Canada.",
    });
    expect(text).toBeDefined();
  }, 30000);
});
