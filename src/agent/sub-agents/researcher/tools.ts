import { tool } from "ai";
import { z } from "zod";
import axios from "axios";
import {
  initBrowser,
  extractContent,
  browserConfig,
  ScrapingResult,
} from "@/services/playwright";
import { Browser } from "playwright";

interface TavilySearchToolOptions {
  onFindResults?: (
    references: {
      title: string;
      url: string;
      content: string;
      score: number;
    }[]
  ) => void;
}

export const createTavilySearchTool = (options?: TavilySearchToolOptions) =>
  tool({
    description: "Search for data using the Tavily Web Search API.",
    parameters: z.object({
      query: z.string().describe("The search query to execute on Tavily."),
      // include_domains: z
      //   .array(z.string())
      //   .optional()
      //   .describe("The domains to include in the search."),
    }),
    execute: async ({
      query,
    }: // include_domains,
    {
      query: string;
      // include_domains: string[];
    }) => {
      try {
        const { data } = await axios.post("https://api.tavily.com/search", {
          api_key: process.env.TAVILY_API_KEY,
          query,
          search_depth: "basic",
          topic: "general",
          max_results: 10,
          include_images: false,
          include_answer: true,
          // include_domains,
          use_cache: false,
        });

        console.log(`Search results: ${JSON.stringify(data)}`);

        options?.onFindResults?.(data.results);

        return JSON.stringify(data);
      } catch (error) {
        console.error("Error in TavilySearchTool:", error);
        return `Error: ${error}`;
      }
    },
  });

export const createPlaywrightTool = () =>
  tool({
    description:
      "A tool that can perform web searches and return the results in a structured format.",
    parameters: z.object({
      url: z.string().describe("The url of the page to scrape."),
      objective: z.string().describe("The objective of the search."),
    }),
    execute: async ({ url, objective }) => {
      let browser: Browser | null = null;
      let result: ScrapingResult;

      try {
        // Initialize browser
        browser = await initBrowser();
        const context = await browser.newContext();
        const page = await context.newPage();

        // Configure timeouts
        await page.setDefaultTimeout(browserConfig.timeout);
        await page.setDefaultNavigationTimeout(browserConfig.timeout);

        // Navigate to URL
        await page.goto(url, { waitUntil: "load" });

        // Extract content
        const extracted = await extractContent(page, objective);

        result = {
          title: extracted.title || "",
          content: extracted.content.slice(2000) || "",
          links: extracted.links,
          metadata: {
            url,
            timestamp: new Date().toISOString(),
            status: "success",
          },
        };
      } catch (error) {
        console.error("Error in PlaywrightTool:", error);
        result = {
          title: "",
          content: "",
          metadata: {
            url,
            timestamp: new Date().toISOString(),
            status: "error",
            message:
              error instanceof Error ? error.message : "Unknown error occurred",
          },
        };
      } finally {
        // Ensure browser is closed
        if (browser) {
          await browser.close();
        }
      }

      return result;
    },
  });
