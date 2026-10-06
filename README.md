# 🧾 BillWise AI

> An AI-powered receipt analyzer and smart bill-splitting application that helps users understand bills, verify expenses, split payments, and share expense summaries.

## 🚀 Live Demo

🔗 **Live Application:**  
https://billwise-ai1.streamlit.app/

🔗 **GitHub Repository:**  
https://github.com/srinijaagangulaa-lab/BillWiseAI

---
## 📸 Screenshots

![BillWise AI Dashboard](screenshots/dashboard.png)

## 📌 Overview

**BillWise AI** is a multimodal AI-powered expense management application built using **Python, Streamlit, and Google Gemini**.

Users can upload a receipt image, and BillWise AI extracts important information such as merchant details, items, prices, taxes, discounts, and the final amount.

The application can then:

- Analyze receipt images using AI
- Extract structured bill information
- Verify bill calculations
- Split bills among multiple people
- Calculate individual shares
- Generate expense summaries
- Answer questions about the uploaded receipt
- Share complete bill summaries
- Send individual expense shares through email
- Prepare WhatsApp messages for easy sharing
- Integrate with Twilio WhatsApp for messaging tests

---

## ✨ Features

### 🧾 AI Receipt Analysis

Upload a receipt image and let Gemini analyze it.

The application extracts:

- Merchant name
- Receipt number
- Date and time
- Items
- Quantity
- Unit price
- Total price
- Subtotal
- Tax
- Discount
- Tip/service charge
- Final total
- Payment method
- Notes or uncertainties

---

### 🧮 Smart Bill Splitting

BillWise AI provides multiple ways to split expenses.

Users can split the bill:

- Equally among participants
- Based on selected items
- Among multiple participants

The application calculates each person's share automatically.

---

### 👥 Participant Management

Users can add participant details such as:

- Name
- Email
- WhatsApp/phone number
- Calculated share

This makes it easier to distribute individual payment information.

---

### ✅ Bill Verification

BillWise AI performs arithmetic checks to verify whether:

- Item totals match
- Subtotal is correct
- Tax and discount calculations are consistent
- Final bill amount is correct
- Split amounts reconcile with the total bill

---

### 💬 AI Receipt Chat

Users can interact with the analyzed receipt and ask questions about it.

Examples:

```text
What is the total bill?

How much did we spend on food?

What items were purchased?

How much does each person need to pay?
