# BillWise AI --- Project Specification

## 1. Project Overview

**Project Name:** BillWise AI

**Project Type:** Multimodal AI Receipt Analyzer, Expense Tracker, and
Bill Splitter

**Primary Stack:** - Python - Streamlit - Google Gemini API - JSON
structured data - Optional action service: WhatsApp via Twilio, Email
via Gmail SMTP, or Telegram

BillWise AI is a Streamlit application that allows a user to upload a
photograph of a receipt or bill. Gemini's multimodal capabilities
analyze the image and extract structured expense information such as
merchant name, date, individual items, quantities, prices, subtotal,
tax, discount, and total.

The application then presents the extracted information in a clear
interface, validates arithmetic where possible, allows the user to split
the bill, and provides a conversational AI interface for asking
questions about the receipt.

The application can generate a final expense summary and send that
summary through a configured action channel.

This project is an independent adaptation of the architecture used in
the workshop's MacroSnap reference application. It should preserve the
general pattern:

    onboarding → image input → Gemini vision → structured/useful result
    → conversation → summary → action

The application must be developed incrementally and should not introduce
unnecessary technologies or features before the core workflow is
working.

------------------------------------------------------------------------

## 2. Problem Statement

People frequently need to understand and divide restaurant bills,
grocery receipts, shopping receipts, and other itemized expenses.

Manual processing requires users to: - read the receipt, - identify each
item, - calculate totals, - account for tax or discounts, - determine
individual shares, - and communicate the final amounts to other people.

BillWise AI reduces this manual work by allowing a user to photograph a
receipt and use AI to extract and analyze the information.

------------------------------------------------------------------------

## 3. Project Goals

The project must:

1.  Accept a receipt image from the user.
2.  Send the image to Gemini for multimodal analysis.
3.  Extract structured receipt information.
4.  Display the extracted information clearly.
5.  Validate basic arithmetic using Python rather than relying only on
    AI arithmetic.
6.  Support equal bill splitting.
7.  Support item-based bill splitting.
8.  Provide an AI chat interface grounded in the current receipt.
9.  Generate a concise final expense summary.
10. Provide an action button for sending the summary.
11. Protect API credentials through Streamlit secrets.
12. Run locally through Streamlit.
13. Be deployable through Streamlit Community Cloud.
14. Keep the implementation understandable to a student learning AI
    application development.

------------------------------------------------------------------------

## 4. Non-Goals for the Initial Version

The initial version must NOT require:

-   OpenCV
-   MediaPipe
-   custom machine-learning model training
-   custom OCR model
-   React
-   Django
-   a complex backend server
-   user authentication
-   a production database
-   payment processing
-   automatic financial transactions
-   unnecessary third-party services

A database and advanced analytics may be considered as future
enhancements after the core application is stable.

------------------------------------------------------------------------

## 5. Target User

The primary user is a student or individual who wants to quickly analyze
and split a physical or digital receipt.

Typical scenario:

1.  User opens BillWise AI.
2.  User enters their name and required sharing information.
3.  User uploads a receipt photograph.
4.  AI analyzes the receipt.
5.  User reviews the extracted information.
6.  User chooses equal or item-based splitting.
7.  User asks questions about the bill if needed.
8.  User generates a final summary.
9.  User sends the summary to the selected destination.

------------------------------------------------------------------------

# 6. Core User Journey

``` text
User
  |
  v
Onboarding
  |
  v
Receipt Upload
  |
  v
Gemini Vision
  |
  v
Structured Receipt Data
  |
  v
Validation
  |
  +--------------------+
  |                    |
  v                    v
Receipt Analysis    Bill Splitter
  |                    |
  +---------+----------+
            |
            v
       AI Bill Chat
            |
            v
      Final Summary
            |
            v
       Action/Share
```

------------------------------------------------------------------------

# 7. Functional Requirements

## 7.1 Onboarding

The application must collect the minimum information required for the
session.

At minimum:

-   User name
-   Destination information required by the selected action service

The onboarding form must:

-   validate required fields,
-   display a warning when required fields are missing,
-   store the values in `st.session_state`,
-   initialize the Gemini conversation,
-   initialize the message history,
-   mark the user as onboarded,
-   rerun the application into the main interface.

The onboarding pattern should follow the MacroSnap reference
architecture.

------------------------------------------------------------------------

## 7.2 Receipt Upload

The application must allow the user to upload receipt images.

Supported initial formats:

-   JPG
-   JPEG
-   PNG

The uploaded image must:

-   be displayed in the chat/interface,
-   be converted to bytes,
-   be passed to Gemini using the Gemini SDK image part mechanism.

The application should not require a separate OCR library for the
initial implementation.

------------------------------------------------------------------------

## 7.3 Receipt Image Analysis

Gemini must analyze the receipt image and extract relevant information.

The system prompt must instruct Gemini to:

-   focus on the receipt,
-   avoid inventing unreadable information,
-   distinguish detected values from uncertain values,
-   return structured information,
-   preserve the original currency when identifiable,
-   identify missing values explicitly,
-   avoid claiming certainty when the image is unclear.

------------------------------------------------------------------------

## 7.4 Structured Receipt Schema

The preferred internal representation is JSON.

Example:

``` json
{
  "merchant": "ABC Restaurant",
  "date": "2026-09-28",
  "currency": "INR",
  "items": [
    {
      "name": "Chicken Biryani",
      "quantity": 1,
      "unit_price": 280.0,
      "total_price": 280.0
    }
  ],
  "subtotal": 280.0,
  "tax": 14.0,
  "discount": 0.0,
  "total": 294.0
}
```

The implementation must handle missing fields gracefully.

For example:

``` json
{
  "tax": null
}
```

is preferable to inventing a tax value.

------------------------------------------------------------------------

# 8. Receipt Data Fields

The system should attempt to extract:

### Merchant

Name of restaurant, store, business, or merchant.

### Date

Receipt transaction date if visible.

### Currency

Currency symbol or currency code when identifiable.

### Items

Each item should contain:

-   name
-   quantity
-   unit price when available
-   total price

### Subtotal

Amount before tax/fees where available.

### Tax

Tax amount where available.

This may include multiple tax components such as CGST or SGST.

### Discount

Discount amount where available.

### Total

Final payable amount.

------------------------------------------------------------------------

# 9. Uncertainty Handling

The AI must not fabricate values.

If the receipt contains an unclear amount:

``` text
Tax: unclear
```

is preferable to:

``` text
Tax: ₹35
```

when ₹35 cannot be reliably read.

The UI should communicate uncertainty.

Example:

``` text
⚠️ Some receipt information may require verification.
```

------------------------------------------------------------------------

# 10. Receipt Verification

Python must perform arithmetic validation where sufficient data is
available.

Example:

``` text
Item total = ₹700
Tax = ₹35
Discount = ₹0

Expected total = ₹735
Detected total = ₹735

Status: Verified
```

If the values do not match:

``` text
⚠️ Possible mismatch

Calculated total: ₹725
Receipt total: ₹735
Difference: ₹10
```

The application must not silently overwrite the receipt's detected
total.

AI is responsible for extraction and interpretation.

Python is responsible for deterministic calculations.

------------------------------------------------------------------------

# 11. Expense Display

After successful extraction, the UI must display:

-   merchant
-   date
-   currency
-   item table
-   subtotal
-   tax
-   discount
-   total
-   verification status

The item table should be readable and suitable for a Streamlit
interface.

------------------------------------------------------------------------

# 12. Equal Bill Split

The user must be able to enter the number of people.

Example:

``` text
Total = ₹900
People = 3

Person 1 = ₹300
Person 2 = ₹300
Person 3 = ₹300
```

The application must validate:

-   number of people is a positive integer,
-   a valid receipt total exists.

The displayed shares should sum to the receipt total, subject to
currency rounding.

------------------------------------------------------------------------

# 13. Named Bill Split

The user should be able to provide names.

Example:

``` text
Srinija
Rahul
Anu
```

The application should display the calculated amount for each person.

------------------------------------------------------------------------

# 14. Item-Based Bill Split

The application should support assigning items to people.

Example:

``` text
Chicken Biryani → Srinija
Pizza → Rahul
Fries → Anu
```

The application calculates each person's item subtotal.

The treatment of shared tax, service charges, and discounts must be
explicit.

Initial implementation should use a deterministic allocation rule and
display that rule to the user.

The final individual amounts must reconcile with the bill total whenever
sufficient receipt information is available.

------------------------------------------------------------------------

# 15. AI Expense Chat

The application must provide a conversational interface after a receipt
has been analyzed.

Example questions:

-   "What is the most expensive item?"
-   "How much tax did I pay?"
-   "What is the total?"
-   "How many items are on this bill?"
-   "Split this bill between 4 people."
-   "What did I spend more than ₹200 on?"

The AI must receive the current receipt context.

The AI must not invent information that is absent from the receipt.

------------------------------------------------------------------------

# 16. Conversation State

The application must maintain conversation state using Streamlit session
state.

Required conceptual state includes:

``` python
st.session_state.name
st.session_state.messages
st.session_state.chat
st.session_state.receipt_data
st.session_state.onboarded
```

Additional state may be introduced when needed for:

-   split mode,
-   people,
-   assignments,
-   generated summary.

------------------------------------------------------------------------

# 17. Message Representation

The application should use a consistent internal message representation
similar to the reference project.

Example:

``` python
{
    "role": "user",
    "kind": "text",
    "content": "How much was the total?"
}
```

For images:

``` python
{
    "role": "user",
    "kind": "image",
    "content": image_bytes
}
```

Supported message kinds should initially include:

-   `text`
-   `image`

------------------------------------------------------------------------

# 18. Summary Generation

The application must have a dedicated summary prompt.

The summary should include, where available:

-   merchant
-   date
-   total
-   major expense items
-   split mode
-   people
-   individual amounts
-   verification status

Example:

``` text
🧾 BILLWISE AI SUMMARY

Merchant: ABC Restaurant
Date: 28 Sep 2026

Total: ₹735

Split: 3 people

Srinija: ₹245
Rahul: ₹245
Anu: ₹245

Receipt verification: Passed
```

------------------------------------------------------------------------

# 19. Action / Sharing

The architecture should have a single send function for the configured
action channel.

Conceptually:

``` python
send_summary(destination, summary)
```

The implementation may use:

-   Twilio WhatsApp
-   Gmail SMTP
-   Telegram

The action service should be isolated from receipt analysis logic.

The rest of the application should not need to know the internal
implementation details of the sending provider.

------------------------------------------------------------------------

# 20. Prompt Architecture

Prompts must be stored in:

``` text
prompts.py
```

The application should have at least:

``` python
SYSTEM_PROMPT
SUMMARY_REQUEST_PROMPT
WELCOME_MESSAGE_TEMPLATE
```

Additional specialized prompts may be added if required.

The system prompt should define BillWise AI's role and limitations.

The summary prompt should request a concise final summary.

The welcome template should provide a friendly initial message.

------------------------------------------------------------------------

# 21. Suggested Project Structure

Initial structure:

``` text
BillWise_AI/
│
├── app.py
├── prompts.py
├── requirements.txt
├── .gitignore
├── README.md
│
└── .streamlit/
    └── secrets.toml
```

As the application becomes larger, logic may be separated into modules
such as:

``` text
receipt_parser.py
bill_splitter.py
gemini_service.py
utils.py
```

These should only be introduced when they improve maintainability.

------------------------------------------------------------------------

# 22. Technology Requirements

The initial application should use:

-   Python
-   Streamlit
-   Google Gemini API
-   Python standard library where possible

Optional:

-   Pandas for tabular display/data handling if useful
-   Twilio for WhatsApp
-   Gmail SMTP for email
-   python-telegram-bot for Telegram

Do not add dependencies without a clear requirement.

------------------------------------------------------------------------

# 23. Secrets Management

Secrets must never be hard-coded into source files.

Local development should use:

``` text
.streamlit/secrets.toml
```

Example:

``` toml
GEMINI_API_KEY = "your-gemini-api-key"
```

If Twilio is selected:

``` toml
TWILIO_ACCOUNT_SID = "your-account-sid"
TWILIO_AUTH_TOKEN = "your-auth-token"
TWILIO_WHATSAPP_FROM = "whatsapp:+..."
TWILIO_CONTENT_SID = "your-content-sid"
```

The exact secret names must remain consistent between `secrets.toml` and
`app.py`.

Secrets must not be committed to GitHub.

------------------------------------------------------------------------

# 24. Security Requirements

The application must:

-   keep API keys in Streamlit secrets,
-   include `secrets.toml` in `.gitignore`,
-   never print API keys,
-   never expose authentication tokens in the UI,
-   avoid storing unnecessary personal information,
-   handle API exceptions without exposing sensitive configuration.

------------------------------------------------------------------------

# 25. Error Handling

The application must gracefully handle:

### Missing API key

Display a useful configuration message.

### Invalid receipt

``` text
I couldn't identify a valid receipt in this image.
Please upload a clearer receipt.
```

### Unclear image

Ask the user to upload a clearer image.

### Gemini/API failure

Display a user-friendly error.

Do not expose secret values or internal credentials.

### Invalid split count

Display a warning.

### Missing receipt total

Disable or prevent bill splitting until a usable total is available.

### Calculation mismatch

Display a verification warning rather than silently changing values.

### Sharing failure

Display an error and allow the user to retry.

------------------------------------------------------------------------

# 26. UI/UX Requirements

The interface should be clean, simple, and student-project friendly.

Primary branding:

``` text
🧾 BillWise AI
```

Suggested description:

``` text
Snap it. Understand it. Split it.
```

The main workflow should be visually obvious:

``` text
Upload Receipt
      ↓
Analyze
      ↓
Review
      ↓
Split
      ↓
Ask
      ↓
Share
```

The UI should use Streamlit native components where practical.

Do not prioritize decorative styling over functionality.

------------------------------------------------------------------------

# 27. AI Behavior Rules

BillWise AI should:

-   analyze receipt images,
-   extract information,
-   answer questions about the current receipt,
-   clearly identify uncertainty,
-   avoid fabricating unreadable values,
-   use the provided receipt context,
-   keep responses concise when appropriate.

BillWise AI should NOT:

-   claim a value was detected when it was not,
-   invent missing receipt items,
-   silently modify receipt totals,
-   present uncertain OCR as confirmed information.

------------------------------------------------------------------------

# 28. Arithmetic Rules

Whenever arithmetic can be performed deterministically, Python should
perform it.

Examples:

``` text
subtotal
tax
discount
total
equal split
item-based split
```

Gemini should not be the sole source of arithmetic calculations.

The application should compare extracted values with calculated values
when possible.

------------------------------------------------------------------------

# 29. Development Process

The project must be developed in stages.

## Stage 1 --- Environment

-   verify Python
-   create virtual environment
-   activate environment

## Stage 2 --- Requirements

-   create `requirements.txt`
-   install dependencies

## Stage 3 --- Prompts

-   create `prompts.py`
-   define system prompt
-   define welcome message
-   define summary prompt

## Stage 4 --- Gemini Connection

-   configure API key
-   create Gemini client
-   test Gemini connection

## Stage 5 --- Onboarding

-   create onboarding form
-   collect user information
-   initialize session state

## Stage 6 --- Chat

-   create chat UI
-   display messages
-   initialize conversation

## Stage 7 --- Input Handling

-   accept receipt image
-   display image
-   convert image to bytes
-   send image to Gemini

## Stage 8 --- Receipt Extraction

-   create extraction prompt
-   request structured data
-   parse JSON
-   validate extracted data

## Stage 9 --- Expense Processing

-   display items
-   calculate totals
-   verify receipt arithmetic

## Stage 10 --- Bill Splitting

-   equal split
-   named split
-   item-based split

## Stage 11 --- AI Bill Chat

-   provide receipt context
-   answer receipt questions
-   maintain conversation state

## Stage 12 --- Summary

-   generate final expense summary

## Stage 13 --- Action

-   connect selected action provider
-   send summary

## Stage 14 --- UI Refinement

-   improve layout
-   improve messages
-   add status indicators
-   improve error presentation

## Stage 15 --- Testing

-   test valid receipts
-   test unclear receipts
-   test missing totals
-   test tax/discount
-   test bill splitting
-   test API failures
-   test sharing failures

## Stage 16 --- Deployment

-   push project to GitHub
-   configure Streamlit secrets
-   deploy to Streamlit Community Cloud
-   perform production smoke test

------------------------------------------------------------------------

# 30. Development Constraint

The application should be implemented incrementally.

Do not generate the entire application before validating each stage.

After every major stage:

1.  run the application,
2.  verify the expected behavior,
3.  fix errors,
4.  then continue.

The developer should avoid replacing working components unnecessarily.

------------------------------------------------------------------------

# 31. Testing Scenarios

The application should eventually be tested with:

### Test 1 --- Simple receipt

One or more items with a clear total.

### Test 2 --- Tax

Receipt containing tax.

### Test 3 --- Discount

Receipt containing a discount.

### Test 4 --- Multiple taxes

For example, separate tax components.

### Test 5 --- Poor image

Expected behavior: uncertainty/error message.

### Test 6 --- Non-receipt image

Expected behavior: application should explain that no valid receipt
could be identified.

### Test 7 --- Equal split

Verify that individual shares reconcile with the total.

### Test 8 --- Item split

Verify that item assignments and final totals reconcile.

### Test 9 --- Missing total

Verify that splitting is prevented or handled safely.

### Test 10 --- API failure

Verify that the application remains usable and shows a clear error.

------------------------------------------------------------------------

# 32. Local Run Requirements

The application must run using:

``` powershell
streamlit run app.py
```

The project should start without requiring manual modification of source
code after secrets are configured.

------------------------------------------------------------------------

# 33. GitHub Requirements

The repository should contain:

``` text
app.py
prompts.py
requirements.txt
.gitignore
README.md
```

The repository must NOT contain:

``` text
.streamlit/secrets.toml
```

or any API key/token.

------------------------------------------------------------------------

# 34. Deployment Requirements

The application should be deployable using Streamlit Community Cloud.

Deployment configuration must include the required secrets through
Streamlit's deployment secrets mechanism.

The deployed application must be tested for:

-   Gemini connection
-   receipt upload
-   receipt extraction
-   bill calculation
-   bill splitting
-   summary generation
-   configured sharing action

------------------------------------------------------------------------

# 35. Future Enhancements

These are NOT required for the initial MVP.

Possible future features:

-   expense history
-   SQLite/Supabase database
-   monthly spending dashboard
-   expense categories
-   charts
-   multiple receipt management
-   recurring expense analysis
-   export to CSV
-   PDF expense reports
-   currency conversion
-   group expense history
-   user accounts
-   advanced receipt correction UI

------------------------------------------------------------------------

# 36. Definition of Done

The project is considered complete when a user can:

1.  Open BillWise AI.
2.  Complete onboarding.
3.  Upload a receipt image.
4.  See the receipt image.
5.  Send the image to Gemini.
6.  Receive structured receipt information.
7.  Review the extracted items and totals.
8.  See validation/calculation status.
9.  Split the bill equally.
10. Split the bill by assigned items.
11. Ask questions about the receipt.
12. Generate a final summary.
13. Send the summary through the configured action channel.
14. Run the application locally.
15. Deploy the application successfully.

------------------------------------------------------------------------

# 37. Implementation Principle

The central engineering principle is:

``` text
AI understands.
Python calculates.
Streamlit presents.
Action service delivers.
```

Gemini should handle multimodal understanding and conversational
interpretation.

Python should handle deterministic calculations and application logic.

Streamlit should handle the user interface and session state.

The configured action provider should handle delivery of the final
summary.

------------------------------------------------------------------------

# 38. Final Architecture

``` text
                    BILLWISE AI
                         |
                         v
                 Streamlit Interface
                         |
             +-----------+-----------+
             |                       |
             v                       v
        Onboarding              Receipt Upload
                                     |
                                     v
                              Gemini Vision
                                     |
                                     v
                           Structured JSON Data
                                     |
                                     v
                              Python Validation
                                     |
                 +-------------------+-------------------+
                 |                   |                   |
                 v                   v                   v
          Receipt Details       Bill Splitter       AI Chat
                 |                   |                   |
                 +-------------------+-------------------+
                                     |
                                     v
                              Summary Generator
                                     |
                                     v
                                Action Tool
                                     |
                    +----------------+----------------+
                    |                |                |
                 WhatsApp          Email           Telegram
```

------------------------------------------------------------------------

# 39. Reference Architecture Relationship

BillWise AI is based on the same conceptual application pattern as the
workshop's MacroSnap project:

``` text
MacroSnap:
Onboarding
    ↓
Gemini chat
    ↓
Meal image
    ↓
Nutrition response
    ↓
Summary
    ↓
WhatsApp

BillWise AI:
Onboarding
    ↓
Gemini chat
    ↓
Receipt image
    ↓
Structured expense response
    ↓
Bill analysis/splitting
    ↓
Summary
    ↓
WhatsApp / Email / Telegram
```

The implementation should preserve this architectural simplicity while
adding the receipt-specific structured-data and calculation
requirements.

------------------------------------------------------------------------

# 40. Instruction to the Development Agent

Build BillWise AI according to this specification.

Do not skip core stages.

Do not implement unrelated features.

Do not introduce unnecessary frameworks.

Do not hard-code secrets.

Do not fabricate receipt information.

Do not rely on Gemini for arithmetic when Python can calculate it
deterministically.

Keep the application modular and understandable.

When an implementation decision is not specified, choose the simplest
approach that preserves the architecture and goals described in this
document.

The project should be developed, tested, and validated incrementally.
