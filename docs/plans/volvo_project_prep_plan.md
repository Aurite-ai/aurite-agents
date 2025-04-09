# Volvo Dealership AI Project - Preparatory Plan

**Objective:** Conduct preliminary research and planning while awaiting specific data, access, and requirements from the Volvo dealership client. This preparation aims to establish foundational knowledge about relevant automotive data standards, dealership systems, and communication technologies.

**Context:** Based on initial discussions (Slack conversation 4/8/2025), the project involves leveraging customer data (calls, chats, CRM, service history) to build AI tools. Potential applications include customer persona generation, recommendation systems (car purchase/maintenance), recall management, abandoned customer analysis, campaign insights, and service follow-up improvements. There's a need to reconcile potential differences in emphasis between recommendation systems (Ryan) and data centralization/communication efficiency (Paul).

**Preparatory Tasks:**

1.  **Research Automotive Data Standards:**
    *   [X] Investigate standard methods for VIN decoding (make, model, year, trim, engine, features). Identify potential public APIs, libraries, or databases (e.g., NHTSA VIN API).
        *   **Finding:** The NHTSA vPIC API (`https://vpic.nhtsa.dot.gov/api/`) is a primary source for US VIN decoding.
        *   **Capabilities:**
            *   Decodes full or partial VINs (single or batch up to 50).
            *   Requires VIN, recommends `modelYear`.
            *   Returns detailed vehicle specs (make, model, year, engine, body class, etc.) in various formats (JSON available).
            *   Provides endpoints to list makes, models, variables, etc.
        *   **Offline Option:** A downloadable MS SQL database (`vPICList_lite`) allows for local VIN decoding via a stored procedure (`spVinDecode`). This is a strong candidate for robust, high-volume decoding.
    *   [X] Research common taxonomies or classification systems for vehicle features, options, packages, and service types used in the automotive industry.
        *   **Finding:** The NHTSA vPIC API provides a `GetVehicleVariableList` endpoint returning 144 standardized variables.
        *   **Taxonomy:** Variables are categorized by `GroupName` (e.g., Engine, Exterior, Interior, Mechanical, Safety Systems), providing a useful taxonomy.
        *   **Values:** Variables have defined data types; `lookup` types have predefined value sets (retrievable via `GetVehicleVariableValuesList`).
        *   **Utility:** This list offers a strong baseline for structuring vehicle feature data for personas and recommendations.
    *   *Goal:* Understand how to structure vehicle data consistently for personas and potential recommendation engines.

2.  **Preliminary Research on Mentioned Systems:**
    *   [ ] **Impel AI:** Gather public information on features, capabilities, potential APIs, and data export options (especially conversation history).
    *   [ ] **VinSolutions/Mastermind CRM:** Research typical data fields, functionalities, and potential API/integration points.
    *   [ ] **CDK Global / DealerTrack DMS:** Understand general capabilities, data typically stored, and common integration methods.
    *   [ ] **Xtime:** Briefly understand its role in scheduling.
    *   [ ] **Dealerware:** Briefly understand its role in loaner vehicles.
    *   *Goal:* Gain a high-level understanding of the dealership's existing tech stack and potential data access points.

3.  **Explore SMS/MMS Chatbot Technologies:**
    *   [ ] Identify potential platforms, libraries, or services for building/integrating SMS/MMS chatbots (e.g., Twilio, Vonage, custom builds).
    *   [ ] Research common features, integration patterns, costs, and limitations relevant to dealership communication workflows.
    *   *Goal:* Prepare for potential development of text-based communication tools, as highlighted by Paul.

4.  **Draft Initial Persona Schema:**
    *   [ ] Outline potential JSON schema or data structures for the two identified persona types:
        *   Persona Type 1: Prospective Car Buyer (Focus: General car preferences)
        *   Persona Type 2: Existing Car Owner (Focus: Specific car, maintenance, upgrades)
    *   [ ] Consider fields derived from potential data sources and the research in Task 1.
    *   *Goal:* Provide a concrete starting point for persona definition and Blake's work on question generation.

**Next Steps:**

*   Begin executing Task 1: Research Automotive Data Standards.
*   Document findings within this plan.
*   Consult with Ryan on findings and schema drafts.
