# Notion Teamspace: Document Hub Update Plan

## 1. Objective

This document outlines the steps required to fix the issue of the "Document Hub" not correctly displaying documents from initiative-specific "Documents" pages. The root cause is that documents are not automatically linked to their parent initiative and require a manual relation to be set.

## 2. The Plan

The solution is to manually link each document in the "Document Hub" to its corresponding project in the "Project Hub".

### Step-by-Step Instructions

1.  **Navigate to the "Document Hub"**:
    *   Open your Notion workspace and go to the "Resources" page.
    *   Click on the "Document Hub" database to open it.

2.  **Identify Unlinked Documents**:
    *   Look for documents where the "Related Initiative" property is empty. These are the documents that need to be updated.

3.  **Edit the "Related Initiative" Property**:
    *   For each unlinked document, click into the empty "Related Initiative" cell.
    *   A search box will appear, allowing you to search for pages in the "Project Hub".

4.  **Select the Correct Project**:
    *   Start typing the name of the project that the document belongs to (e.g., "Test Framework Initiative").
    *   Select the correct project from the list that appears.

5.  **Repeat for All Unlinked Documents**:
    *   Continue this process for every document in the "Document Hub" that is missing the "Related Initiative" link.

## 3. Verification

Once you have completed these steps, any filtered views of the "Document Hub" that rely on the "Related Initiative" property will now work as expected. You can verify this by creating a filtered view on a page that only shows documents related to a specific project.

## 4. Future Prevention

To prevent this issue in the future, ensure that every new document created in the "Document Hub" has its "Related Initiative" property set at the time of creation.
