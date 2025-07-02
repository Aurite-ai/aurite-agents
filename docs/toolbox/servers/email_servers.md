# Email Servers

This document provides details on the packaged email-related MCP servers available in the Aurite Agents framework.

## Gmail Server (`gmail_server`)

This server provides tools to interact with the Gmail API, allowing agents to send, read, and manage emails.

**Configuration File**: `config/mcp_servers/email_servers.json`

### Authentication Setup (Manual Action Required)

This server uses OAuth 2.0 for authentication and requires manual setup to grant access to your Gmail account. The server configuration uses the `command` and `args` method to run the MCP server. The `npx` command will automatically install and run the server on your computer. Since `npx` is a Node.js command, you must have Node.js installed.

The setup process is similar to the installation steps in the [official server repository](https://github.com/GongRzhe/Gmail-MCP-Server), with specific instructions for the Aurite framework below.

**1. Create Google Cloud OAuth Credentials:**

*   Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project or select an existing one.
*   Enable the **Gmail API** for your project from the **APIs & Services > Library**.
*   Go to **APIs & Services > Credentials** and click **+ CREATE CREDENTIALS** > **OAuth client ID**.
*   For **Application type**, select **Desktop app**.
*   If prompted, configure the consent screen. For **User Type**, select **External**. You only need one person to set up the initial OAuth credentials; other team members can be added as **Test Users** in the OAuth consent screen configuration.
*   After creating the client ID, download the JSON file.

**2. Configure the Credentials File:**

*   Rename the downloaded file to `gcp-oauth.keys.json`.
*   Place this file in a `.gmail-mcp` directory in your home folder (e.g., `~/.gmail-mcp/`).
*   The content of `gcp-oauth.keys.json` should look like this:
    ```json
    {
      "installed": {
        "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
        "client_secret": "YOUR_CLIENT_SECRET",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"]
      }
    }
    ```

**3. Run First-time Authorization:**

*   Before the framework can use the server, you must run a one-time authorization command in your terminal. This will open a browser window for you to grant permission.
    ```bash
    npx @gongrzhe/server-gmail-autoauth-mcp auth
    ```
*   After you approve, the server will store a token in `~/.gmail-mcp/credentials.json` for future use.

**Note on OAuth:** This manual setup is similar to the "Login with Google" buttons you see on websites. For a production application like a Chrome extension, you would typically build a user-facing OAuth consent screen to handle this process automatically for your users.

### Available Tools

*   `send_email`: Sends a new email.
*   `draft_email`: Drafts a new email.
*   `read_email`: Retrieves the content of a specific email.
*   `search_emails`: Searches for emails using Gmail search syntax.
*   `modify_email`: Modifies email labels (e.g., move to folders).
*   `delete_email`: Permanently deletes an email. **Note:** This tool may fail due to insufficient OAuth permissions granted by the server.
*   `list_email_labels`: Retrieves all available Gmail labels.
*   `batch_modify_emails`: Modifies labels for multiple emails.
*   `batch_delete_emails`: Deletes multiple emails.
*   `create_label`: Creates a new Gmail label.
*   `update_label`: Updates an existing label.
*   `delete_label`: Deletes a label.
*   `get_or_create_label`: Gets a label by name or creates it.
*   `download_attachment`: Downloads an email attachment.

### Relevant Agents

*   **`gmail_agent`**: An agent that can use the `gmail_server` to answer questions and manage emails.
    *   **Configuration File**: `config/agents/email_agents.json`
