# Project Category: Data Processing Pipelines

## Real-World Business Use Cases
Data processing pipelines are the backbone of modern data analytics and business intelligence. Companies use them to transform raw data into actionable insights.
*   **Market Research:** A company might use a pipeline to scrape the web for reviews of a competitor's product, analyze the sentiment of those reviews, and generate a report on the competitor's strengths and weaknesses.
*   **Social Media Monitoring:** Brands automatically track mentions on social media, analyze the sentiment of the posts, and route urgent issues to a human support agent.
*   **Financial Analysis:** Hedge funds can ingest news articles, press releases, and social media posts, process them to identify market signals, and generate daily trading briefs for analysts.

---

Data processing pipelines are an excellent way to learn how to build multi-agent workflows. In these projects, you will chain multiple specialized agents together, where the output of one agent becomes the input for the next. This pattern is common in real-world applications for automating complex tasks.

---

## The Scenario

You are a **Junior Market Analyst** at **"Momentum Media"**, a dynamic marketing firm that helps video game studios understand their audience.

**The Task:** Your manager has asked you to create an automated daily briefing on the competitive landscape. Specifically, she wants a report that identifies the top-selling games on Steam and summarizes the latest news about them. This will help your clients understand what's currently popular and how the media is covering their competitors.

**Your Goal:** Build a three-agent workflow that automates this entire process.

### Core Concepts to Apply
*   **Linear Workflows:** Defining a sequence of agents to run in order.
*   **Structured Output:** Using `config_validation_schema` to force an agent to produce reliable JSON data.
*   **Tool Integration:** Using tools for data retrieval (`game_trends_mcp`), web research (`duckduckgo_search`), and file I/O (`desktop_commander`).

### The Workflow Structure
Your project will follow this three-step workflow:

1.  **Agent 1: The "Trend Spotter"**
    *   **Role:** This agent's job is to retrieve the initial dataset.
    *   **Tools:** It will use the `game_trends_mcp` tool server to get the top 3-5 best-selling games on Steam.
    *   **Output:** It should produce a clean, structured list of the game titles.

2.  **Agent 2: The "News Hound"**
    *   **Role:** This agent takes the list of games and enriches it with current events.
    *   **Tools:** It will use the `duckduckgo_search` tool to find a recent news article or review for each game and then summarize it.
    *   **Output:** It passes along a more detailed, structured set of data containing each game's title and its news summary.

3.  **Agent 3: The "Briefing Drafter"**
    *   **Role:** This agent's job is to present the final, processed data in a professional, human-readable format.
    *   **Tools:** It will use the `desktop_commander` server to write its final report to a Markdown file named `daily_gaming_brief.md`.
    *   **Output:** A final message indicating the report has been saved.

### Tips
- Start by building and testing each agent in isolation. Ensure each agent can complete its task. Start with the first agent, and when it is complete, use the output from the first agent to build and test the second agent. Once all of the agents are working on their own, start connecting them in a simple workflow. Start with a simple workflow that only contains the first two agents, and then add more agents as steps when the workflow is outputting the correct response.

---

## Other Project Ideas

If you'd like to try a different scenario, use these ideas as inspiration. You can adapt the three-step workflow (Gather, Process, Report) to any of them.

### 1. App Store Market Analyzer
*   **Goal:** Analyze the top apps in a specific category on the Google Play Store and summarize user sentiment.
*   **Workflow:**
    1.  **Agent 1 (`App Finder`):** Uses `appinsightmcp`'s `google-play-list` tool to find the top 5 free apps in the "Social" category.
    2.  **Agent 2 (`Review Analyzer`):** For each app, uses `appinsightmcp`'s `google-play-reviews` tool to get the most recent reviews. It then performs sentiment analysis on the reviews (positive, negative, neutral).
    3.  **Agent 3 (`Market Analyst`):** Creates a report summarizing the sentiment for each app and saves it to `app_market_report.md`.

### 2. Social Media Comment Processor
*   **Goal:** Read a file of raw text comments, analyze them, and generate a summary report.
*   **Workflow:**
    1.  **Agent 1 (`Comment Reader`):** Uses `desktop_commander`'s `read_file` tool to ingest a `.txt` file of comments.
    2.  **Agent 2 (`Sentiment Analyzer`):** Processes each comment, using a `config_validation_schema` to output a structured analysis (e.g., `{ "sentiment": "positive", "topics": ["topic1"] }`).
    3.  **Agent 3 (`Report Generator`):** Aggregates the structured data (e.g., counts sentiment, lists top topics) and saves the results to `comment_summary.md`.

### Your Custom Project
Don't like any of these ideas? You can build your own data processing pipeline that achieves a specific goal. It should chain multiple agents together to complete an overarching task that involves processing real-time data.

---