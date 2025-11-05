How to Run This QuickBooks Web Connector Service

This service syncs Customers, Employees, Invoices, and Journal Entries.

This service is HTTP, not HTTPS. The QBWC will complain. For this to work, you MUST use a tool like ngrok to create a secure (HTTPS) tunnel to this local server.

!! ASSUMPTIONS !!

For this to work, your QuickBooks company file MUST already have:

For Invoices: An "Item" in your Item List named "Services".

For Journal Entries: "Accounts" in your Chart of Accounts named "Checking" and "Office Expenses".

If these do not exist, the InvoiceAddRq or JournalEntryAddRq will fail. You can edit the data arrays at the top of qbwc_service.py to match the items and accounts you do have in your file.

Step-by-Step Guide

1. Install ngrok

Go to ngrok.com and sign up for a free account.

Download and unzip the ngrok executable.

Follow their instructions to add your "authtoken" (this is a one-time setup).

2. Run the Python Service

Open your terminal, navigate to the directory with qbwc_service.py, and run it:

python qbwc_service.py


You should see: Starting QBWC SOAP Service on http://localhost:8000/...

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

Go to File > Update Web Services. This will open the Web Connector application.

If you already added the app:

Find "My Python Customer Sync" in the list.

Click Remove.

Now proceed to add the application again. (This is the easiest way to update the URL).

Add the Application:

Click Add an Application.

Select the example.qwc file you just edited.

A security window will pop up. Authorize the service.

The application will appear in your list.

Enter the password: testpass (this is set in the qbwc_service.py file).

Check the box on the far left next to the application name.

Click Update Selected.

6. Watch the Sync

You will see activity in your python qbwc_service.py terminal as it processes each job one by one (Customer, Employee, Invoice, etc.). You can then check your QuickBooks company file to see the new records.
