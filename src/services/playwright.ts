import { chromium, Browser, Page } from "playwright";
import { z } from "zod";

// Types for the scraping result
export interface ScrapingResult {
  title: string;
  content: string;
  metadata: {
    url: string;
    timestamp: string;
    status: "success" | "partial" | "error";
    message?: string;
  };
  links?: Array<{ text: string; href: string }>;
}

// Configuration for the browser
export const browserConfig = {
  headless: true,
  timeout: 30000,
};

// Helper function to initialize the browser
export async function initBrowser(): Promise<Browser> {
  return await chromium.launch(browserConfig);
}

// Helper function to extract content based on objective
export async function extractContent(
  page: Page,
  objective: string
): Promise<Partial<ScrapingResult>> {
  const title = await page.title();
  let content = "";

  const textContent = await page.evaluate(() => document.body.innerText);

  content = textContent;

  // Apply objective-specific extraction if needed
  const links = await page.evaluate(() =>
    Array.from(document.querySelectorAll("a"))
      .map((a) => ({
        text: a.textContent?.trim() || "",
        href: a.href,
      }))
      .filter((link) => link.href.startsWith("http"))
  );

  return {
    title,
    content,
    links,
  };
}

// Example usage:
/*
const playwrightTool = createPlaywrightTool();
const result = await playwrightTool.execute({
  url: 'https://example.com',
  objective: 'Extract main content'
});
*/
