# Web Search MCP Servers

This document provides a list of pre-configured MCP servers for Web Search that are included with the `aurite` package. The servers listed below are defined in the `config/mcp_servers/web_search.json` file.

## Available Servers

### `exa_search`

*   **Description**: Fast, intelligent web search and crawling powered by Exa AI. Combines embeddings and traditional search to deliver the best results for LLMs.
*   **Configuration File**: `config/mcp_servers/web_search.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `web_search_exa` | Search the web using Exa AI - performs real-time web searches and can scrape content from specific URLs. Supports configurable result counts and returns the content from the most relevant websites. |
| `research_paper_search` | Search across 100M+ research papers with full text access using Exa AI - performs targeted academic paper searches with deep research content coverage. Returns detailed information about relevant academic papers including titles, authors, publication dates, and full text excerpts. |
| `company_research` | Research companies using Exa AI - performs targeted searches of company websites to gather comprehensive information about businesses. Returns detailed information from company websites including about pages, pricing, FAQs, blogs, and other relevant content. |
| `crawling` | Extract content from specific URLs using Exa AI - performs targeted crawling of web pages to retrieve their full content. Useful for reading articles, PDFs, or any web page when you have the exact URL. |
| `competitor_finder` | Find competitors of a company using Exa AI - performs targeted searches to identify businesses that offer similar products or services. Describe what the company does and optionally provide the company's website to exclude it from results. |
| `linkedin_search` | Search LinkedIn for companies using Exa AI. Simply include company URL, or company name, with 'company page' appended in your query. |
| `wikipedia_search_exa` | Search Wikipedia using Exa AI - performs searches specifically within Wikipedia.org and returns relevant content from Wikipedia pages. |
| `github_search` | Search GitHub repositories using Exa AI - performs real-time searches on GitHub.com to find relevant repositories and GitHub accounts. |

### `duckduckgo_search`

*   **Description**: Enable web search capabilities through DuckDuckGo. Fetch and parse webpage content intelligently for enhanced LLM interaction.
*   **Configuration File**: `config/mcp_servers/web_search.json`

**Tools:**
| Tool Name | Description |
| :-------- | :---------- |
| `search` | Search DuckDuckGo and return formatted results. **Args:** `query`: The search query string, `max_results`: Maximum number of results to return (default: 10), `ctx`: MCP context for logging |
| `fetch_content` | Fetch and parse content from a webpage URL. **Args:** `url`: The webpage URL to fetch content from, `ctx`: MCP context for logging |

### `paper_search`

*   **Description**: Search and download academic papers from multiple sources like arXiv and PubMed. Enhance your research workflow with seamless integration into LLM applications, allowing for efficient access to scholarly content.
*   **Configuration File**: `config/mcp_servers/web_search.json`

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
