describe("test chat api", () => {
  it("should return a response", async () => {
    const response = await fetch("http://localhost:4444/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages: [{ role: "user", content: "Hello, say this is a test." }],
        model: "gpt-4o",
      }),
    });

    console.log(response);

    expect(response.status).toBe(200);

    const data = await response.json();
    expect(data).toBeDefined();
  });
});
