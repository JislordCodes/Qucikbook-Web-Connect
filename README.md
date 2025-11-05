How to Run This QuickBooks Web Connector Service

For this to work, you MUST use a tool like ngrok to create a secure (HTTPS) tunnel to this local server.

Step-by-Step Guide

1. Install ngrok

ngrok is a tool that creates a secure, public URL (like https://xyz.ngrok.io) that points to your local server.

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


ngrok will give you a public "Forwarding" URL. You need the https one:

Forwarding                    [https://2a1b-3c4d-5e6f-7g8h.ngrok-free.app](https://2a1b-3c4d-5e6f-7g8h.ngrok-free.app) -> http://localhost:8000


Copy this HTTPS URL.

4. Edit the .qwc File

Open example.qwc in a text editor.

Find the <AppURL> line.

Replace http://localhost:8000/service with your ngrok HTTPS URL.

Example:
<AppURL>https://2a1b-3c4d-5e6f-7g8h.ngrok-free.app/service</AppURL>

Save the file.

5. Configure QuickBooks Web Connector

Open QuickBooks Desktop as an Admin.

Go to File > Update Web Services. This will open the Web Connector application.

Click Add an Application.

Select the example.qwc file you just edited.

A security window will pop up. Authorize the service.

A new application, "My Python Customer Sync," will appear in your list.

Enter the password: testpass (this is set in the qbwc_service.py file).

Check the box on the far left next to the application name.

Click Update Selected.


You will see activity in both terminal windows:

The ngrok terminal will show POST /service requests.

The python qbwc_service.py terminal will show the "QBWC: Called authenticate", "QBWC: Sending job...", and "QBWC: Job received" messages.

Your customers from the CUSTOMERS_TO_SYNC array will now be added to QuickBooks!
