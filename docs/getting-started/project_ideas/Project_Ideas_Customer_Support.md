# Project Category: Customer Support Bots

## Real-World Business Use Cases
Customer support bots are one of the most common applications of AI agents in business. They act as the first point of contact for customers, handling common queries and freeing up human agents to focus on more complex issues.
*   **E-commerce:** An online store's bot can check order statuses, handle returns, and answer questions about products by reading from a database or product catalog file.
*   **Airlines & Travel:** An airline's bot can provide flight status updates, check for weather delays using a live weather tool, and explain baggage policies by consulting internal documents.
*   **Software as a Service (SaaS):** A SaaS company can deploy a bot that guides users through common troubleshooting steps by consulting a knowledge base of technical articles and product manuals.

---

Customer support bots are a classic use case for AI agents. These projects challenge you to build a single, robust agent that can act as the "face" of a company. The key is to write a detailed system prompt that gives the agent a clear personality and a set of rules for how to interact with users and when to use its tools.

For this project, we provide a template notebook that sets up the environment and the knowledge base files for you. Your task is to implement the core logic for the customer support agent.

*   **Template Notebook:** [Project Template](https://colab.research.google.com/drive/1RWe6vutqFwsKweTsEVyCj32-rZDzvnbL?usp=sharing)

Open this notebook to get started. It contains detailed instructions and all the necessary setup code.

---

## The Scenario

You are a **Customer Support Specialist** at **"GadgetCo"**, a fictional, cutting-edge electronics company known for its popular "Smart-Widget" device.

**The Task:** Customers are frequently asking the same questions about the Smart-Widget. Your manager wants you to build an AI-powered support bot named "Chip" to handle these initial queries, freeing up the human support team for more complex issues.

**Your Goal:** Following the instructions in the template notebook, build and test "Chip" to act as the first line of support for GadgetCo.

### Core Concepts to Apply
*   **Advanced System Prompts:** Crafting a detailed persona, rules, and instructions for the agent.
*   **Conditional Tool Use:** Designing an agent that can reason about which tool to use based on the user's query.
*   **Multi-Tool Integration:** Giving a single agent access to multiple tool servers to handle a wide range of requests.

### The Agent's Structure
Your agent will need the following characteristics, which you will define in its `AgentConfig`:

1.  **A Detailed Persona:** The system prompt should define "Chip" as a friendly, patient, and knowledgeable tech support assistant for GadgetCo.
2.  **A Rich Toolset:** The agent will need access to multiple tools:
    *   `local_file_storage`: To read from local files like `manuals/smart_widget_manual.txt` and `faq.md`.
    *   `duckduckgo_search`: To find external troubleshooting guides if the internal documents don't have the answer.
3.  **Clear Rules of Engagement:** The system prompt must give Chip a clear procedure for finding answers:
    *   First, check the `faq.md` document.
    *   If the answer isn't in the FAQ, consult the `manuals/smart_widget_manual.txt` file.
    *   Only if the answer isn't in the internal documents, use `duckduckgo_search`.
    *   Never guess. If an answer can't be found, politely state that and offer to escalate to a human agent.

### Completing the Project
The template notebook guides you through these steps:
1.  **Setup:** It installs Aurite and creates the knowledge base files (`faq.md` and `smart_widget_manual.txt`).
2.  **Your Task:** You will find a cell with the comment `# YOUR CODE HERE`. In this cell, you must create the `AgentConfig` for "Chip" and register it with Aurite.
3.  **Testing:** After implementing Chip, you will uncomment and run the testing cells to see if your agent correctly answers questions based on the FAQ, the manual, and external search.
4.  **Interactive Chat:** Finally, you can uncomment and run the last cell to have a live, interactive conversation with your completed chatbot.

---

## Other Project Ideas

If you'd like to try a different scenario, use these ideas as inspiration. You can adapt the single-agent, multi-tool structure to any of them.

### 1. "Wanderlust Airlines" Booking Assistant
*   **Goal:** Create a support bot for a fictional airline that can check flight statuses and answer questions about travel policies.
*   **Agent Persona:** "Stella," a professional and efficient airline representative.
*   **Tools:**
    *   `local_file_storage`: To read flight information from a local `flight_data.csv` file and to read the company's travel policy from `policy.txt`.
    *   `national_weather_service`: To check for weather delays at the arrival or departure city.
*   **Example Query:** "What's the status of flight WL123 to New York, and can I bring my pet cat?"

### Tips
- Start by creating a comprehensive system prompt that clearly defines your agent's personality, role, and decision-making process. Test the agent with simple queries first to ensure it follows your instructions correctly. Then gradually add more complex scenarios and edge cases. Focus on making the agent's tool selection logic clear and predictable - it should always try internal resources first before searching externally.


### 2. "Campus Helper" University Bot
*   **Goal:** Build an assistant for a university that can answer questions about courses, events, and campus navigation.
*   **Agent Persona:** "Alex," a helpful and knowledgeable student guide.
*   **Tools:**
    *   `local_file_storage`: To read the course catalog from `course_catalog.json` and a list of campus events from `events.md`.
    *   `duckduckgo_search`: To find information about local businesses or transportation near campus.
*   **Example Query:** "Are there any seats left in the 'Intro to Python' course, and what's happening on campus this Friday?"

### Your Custom Project
Don't like any of these ideas? You can build your own customer support bot for any fictional company or service. It should be a single agent with multiple tools that can handle a variety of customer inquiries by consulting internal documents and external resources when needed.

---
