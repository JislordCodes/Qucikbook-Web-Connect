How to Run This QuickBooks Web Connector Service

This service now syncs Customers, Employees, Invoices, and Journal Entries.

It also includes robust logging and automatic retries for failed jobs.

New Feature: Sync Log

A new file, sync_log.csv, will be created in the same directory.

This file contains a detailed record of every single operation, including its status, duration, error message (if any), and the full XML payload that was sent.

!! CRITICAL ASSUMPTIONS !!

For this to work, your QuickBooks company file MUST already have:

For Invoices: An "Item" in your Item List named "Services".

For Journal Entries: "Accounts" in your Chart of Accounts named "Checking" and "Office Expenses".

If these do not exist, the InvoiceAddRq or JournalEntryAddRq will fail. You can edit the data arrays at the top of qbwc_service.py to match the items and accounts you do have in your file.

I have intentionally included a failing job (Invoice "INV-FAIL-TEST") so you can see the retry logic and error logging in action.

Step-by-Step Guide

1. Install ngrok

Go to ngrok.com and sign up for a free account.

Download and unzip the ngrok executable.

Follow their instructions to add your "authtoken" (this is a one-time setup).

2. Run the Python Service

Open your terminal, navigate to the directory with qbwc_service.py, and run it:

python qbwc_service.py


You should see: Starting QBWC SOAP Service on http://localhost:8000/...
And: Logging operations to sync_log.csv

Leave this terminal window open.

3. Run ngrok

Open a second terminal window and run ngrok to expose your port 8000:

ngrok http 8000


ngrok will give you a public "Forwarding" URL. You need the httpss one:

Forwarding                    [https://1a2b-3c4d-5e6f-7g8h.ngrok-free.app](https://1a2b-3c4d-5e6f-7g8h.ngrok-free.app) -> http://localhost:8000


Copy this HTTPS URL.

4. Edit the .qwc File

Open example.qwc (the file from our previous conversation) in a text editor.

Find the <AppURL> line.

Replace the old URL with your new ngrok HTTPS URL.

Example:
<AppURL>https://1a2b-3c4d-5e6f-7g8h.ngrok-free.app/service</AppURL>

Save the file.

5. Configure QuickBooks Web Connector

Open QuickBooks Desktop as an Admin.

Go to File > Update Web Services.

If you already added the app: Find "My Python Customer Sync", click Remove, and then re-add it using the steps below.

Add the Application:

Click Add an Application.

Select the example.qwc file you just edited.

Authorize the service.

Enter the password: testpass

Check the box on the far left and click Update Selected.

6. Watch the Sync

Your Python terminal will show the status of each job, including failures and retries.

Open sync_log.csv (in Excel or a text editor) to see the detailed results. You will see the "INV-FAIL-TEST" job change from "Failed (Retrying...)" to "Failed (Aborted)" after it hits the max retry count.
