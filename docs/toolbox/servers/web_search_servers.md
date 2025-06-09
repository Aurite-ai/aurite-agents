# Web Search MCP Servers

This document provides a list of pre-configured MCP servers for Web Search that are included with the `aurite` package. The servers listed below are defined in the `config/mcp_servers/web_search.json` file.

## Available Servers

### `duckduckgo_search`

*   **Description**: Enable web search capabilities through DuckDuckGo. Fetch and parse webpage content intelligently for enhanced LLM interaction.
*   **Configuration File**: `config/mcp_servers/web_search_servers.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `search` | Search DuckDuckGo and return formatted results. **Args:** `query`: The search query string, `max_results`: Maximum number of results to return (default: 10), `ctx`: MCP context for logging |
| `fetch_content` | Fetch and parse content from a webpage URL. **Args:** `url`: The webpage URL to fetch content from, `ctx`: MCP context for logging |

### `paper_search`

*   **Description**: Search and download academic papers from multiple sources like arXiv and PubMed. Enhance your research workflow with seamless integration into LLM applications, allowing for efficient access to scholarly content.
*   **Configuration File**: `config/mcp_servers/web_search_servers.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `search_arxiv` | Search academic papers from arXiv. **Args:** `query`: Search query string (e.g., 'machine learning'), `max_results`: Maximum number of papers to return (default: 10) |
| `search_pubmed` | Search academic papers from PubMed. **Args:** `query`: Search query string, `max_results`: Maximum number of papers to return (default: 10) |
| `search_biorxiv` | Search academic papers from bioRxiv. **Args:** `query`: Search query string, `max_results`: Maximum number of papers to return (default: 10) |
| `search_medrxiv` | Search academic papers from medRxiv. **Args:** `query`: Search query string, `max_results`: Maximum number of papers to return (default: 10) |
| `search_google_scholar` | Search academic papers from Google Scholar. **Args:** `query`: Search query string, `max_results`: Maximum number of papers to return (default: 10) |

**Excluded**:
The following tools are excluded as the mcp server does not have file read/write access.
| Tool Name | Description |
| :-------- | :---------- |
| `download_arxiv` | Download PDF of an arXiv paper. **Args:** `paper_id`: arXiv paper ID (e.g., '2106.12345'), `save_path`: Directory to save the PDF (default: './downloads') |
| `download_pubmed` | Attempt to download PDF of a PubMed paper. **Args:** `paper_id`: PubMed ID (PMID), `save_path`: Directory to save the PDF |
| `download_biorxiv` | Download PDF of a bioRxiv paper. **Args:** `paper_id`: bioRxiv DOI, `save_path`: Directory to save the PDF |
| `download_medrxiv` | Download PDF of a medRxiv paper. **Args:** `paper_id`: medRxiv DOI, `save_path`: Directory to save the PDF |
| `read_arxiv_paper` | Read and extract text content from an arXiv paper PDF. **Args:** `paper_id`: arXiv paper ID, `save_path`: Directory where the PDF is/will be saved |
| `read_pubmed_paper` | Read and extract text content from a PubMed paper. **Args:** `paper_id`: PubMed ID (PMID), `save_path`: Directory where the PDF would be saved |
| `read_biorxiv_paper` | Read and extract text content from a bioRxiv paper PDF. **Args:** `paper_id`: bioRxiv DOI, `save_path`: Directory where the PDF is/will be saved |
| `read_medrxiv_paper` | Read and extract text content from a medRxiv paper PDF. **Args:** `paper_id`: medRxiv DOI, `save_path`: Directory where the PDF is/will be saved |
