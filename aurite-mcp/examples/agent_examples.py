"""
Examples of using the Aurite Agent framework.
"""

import asyncio
import logging
from pathlib import Path

from src.host.host import MCPHost, HostConfig, ClientConfig, RootConfig
from src.agents.examples import DocumentProcessorWorkflow, ResearchAssistantAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Sample tool server paths - these would point to actual MCP tool servers
TOOLS_SERVER_PATH = Path("examples/weather_server.py")
TEXT_SERVER_PATH = Path("examples/simple/simple_server.py")


async def run_document_processor_example():
    """Run an example of the document processor workflow"""
    logger.info("===== DOCUMENT PROCESSOR WORKFLOW EXAMPLE =====")

    # Configure the host with tool servers
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="text_tools",
                server_path=TEXT_SERVER_PATH.absolute(),
                roots=[
                    RootConfig(
                        name="text", uri="text:///", capabilities=["read", "write"]
                    )
                ],
                capabilities=["tools", "prompts"],
                routing_weight=1.0,
            ),
            ClientConfig(
                client_id="weather_tools",
                server_path=TOOLS_SERVER_PATH.absolute(),
                roots=[
                    RootConfig(name="weather", uri="weather:///", capabilities=["read"])
                ],
                capabilities=["tools"],
                routing_weight=1.0,
            ),
        ]
    )

    # Create and initialize host
    host = MCPHost(config)
    await host.initialize()

    try:
        # Create document processor workflow
        processor = DocumentProcessorWorkflow(host)
        await processor.initialize()

        # Sample document to process
        sample_document = """
        ACME CORPORATION
        QUARTERLY FINANCIAL REPORT
        Q1 2025
        
        Overview:
        ACME Corporation had a strong first quarter, with revenue up 15% year-over-year.
        Net profit increased by 12%, despite ongoing supply chain challenges.
        
        Financial Highlights:
        - Revenue: $78.5M (up 15% YoY)
        - Operating Income: $23.2M (up 10% YoY)
        - Net Profit: $18.7M (up 12% YoY)
        - EPS: $1.45 (up from $1.30 in Q1 2024)
        
        Outlook:
        We expect continued growth in Q2, with potential expansion into European markets.
        Supply chain issues are expected to ease in the second half of the year.
        
        Prepared by: Financial Reporting Team
        Date: April 15, 2025
        """

        # Process the document
        result = await processor.execute({"document_text": sample_document})

        # Show results
        logger.info(f"Workflow completed in {result.get_execution_time():.2f} seconds")
        logger.info(f"Document type: {result.data.get('document_type')}")
        logger.info(f"Document category: {result.data.get('document_category')}")
        logger.info(
            f"Sentiment: {result.data.get('sentiment')} (Score: {result.data.get('sentiment_score')})"
        )
        logger.info(f"Report: {result.data.get('final_report')}")

    finally:
        # Shutdown
        await processor.shutdown()
        await host.shutdown()


async def run_research_assistant_example():
    """Run an example of the research assistant agent"""
    logger.info("===== RESEARCH ASSISTANT AGENT EXAMPLE =====")

    # Configure the host with tool servers
    config = HostConfig(
        clients=[
            ClientConfig(
                client_id="text_tools",
                server_path=TEXT_SERVER_PATH.absolute(),
                roots=[
                    RootConfig(
                        name="text", uri="text:///", capabilities=["read", "write"]
                    )
                ],
                capabilities=["tools", "prompts"],
                routing_weight=1.0,
            ),
            ClientConfig(
                client_id="weather_tools",
                server_path=TOOLS_SERVER_PATH.absolute(),
                roots=[
                    RootConfig(name="weather", uri="weather:///", capabilities=["read"])
                ],
                capabilities=["tools"],
                routing_weight=1.0,
            ),
        ]
    )

    # Create and initialize host
    host = MCPHost(config)
    await host.initialize()

    try:
        # Create research assistant agent
        assistant = ResearchAssistantAgent(host)
        await assistant.initialize()

        # Sample research topic
        topic = "Climate change impacts on ocean ecosystems"

        # Execute research task
        report = await assistant.research_topic(topic, depth="medium")

        # Show results
        logger.info(f"Research completed in {report['execution_time']:.2f} seconds")
        logger.info(f"Success: {report['success']}")

        if report["success"]:
            logger.info(f"Content length: {len(report.get('content', ''))}")
            logger.info(f"Sources: {report.get('sources', [])}")
            logger.info(f"Quality metrics: {report.get('evaluation', {})}")
        else:
            logger.error(f"Research failed: {report.get('error')}")

    finally:
        # Shutdown
        await assistant.shutdown()
        await host.shutdown()


async def main():
    """Run all examples"""
    # Run examples
    await run_document_processor_example()
    await run_research_assistant_example()


if __name__ == "__main__":
    asyncio.run(main())
