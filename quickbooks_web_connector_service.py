import http.server
import xml.etree.ElementTree as ET
import uuid
import html
import datetime

# --- Configuration ---
# These must match what's in your .qwc file
QBWC_USERNAME = "testuser"
QBWC_PASSWORD = "testpass"

# Keep track of active sessions (tickets)
ACTIVE_TICKETS = {}


# This is the "array of objects"

CUSTOMERS_TO_SYNC = [
    {"id": "C1001", "name": "John Doe", "email": "john.doe@example.com", "phone": "555-1234"},
    {"id": "C1002", "name": "Jane Smith", "email": "jane.smith@example.com", "company": "Smith Co."}
]

# Employees
EMPLOYEES_TO_SYNC = [
    {"id": "E101", "first_name": "Sarah", "last_name": "Jenkins", "job_title": "Developer"},
    {"id": "E102", "first_name": "Mike", "last_name": "Brown", "job_title": "Sales Rep"}
]

# Invoices
# **ASSUMPTION**: The Customer 'FullName' (e.g., "John Doe") already exists or is
#                 being added in this batch (which it is).
# **ASSUMPTION**: The Item 'FullName' (e.g., "Services") ALREADY EXISTS in your
#                 QuickBooks Item List. This is critical.

INVOICES_TO_SYNC = [
    {
        "id": "INV-001",
        "customer_name": "John Doe", # Must match a customer's 'Name'
        "txn_date": "2024-10-25",
        "lines": [
            {"item_name": "Services", "desc": "Web Development", "quantity": 10, "rate": 150.00},
            {"item_name": "Services", "desc": "Consulting", "quantity": 2, "rate": 200.00}
        ]
    }
]

# "General Ledger" is a "Journal Entry" in QuickBooks
# **ASSUMPTION**: The Accounts 'FullName' (e.g., "Checking", "Office Expenses")
#                 ALREADY EXIST in your QuickBooks Chart of Accounts.
# The total of debits MUST equal the total of credits.

GL_ENTRIES_TO_SYNC = [
    {
        "id": "GL-001",
        "txn_date": "2024-10-25",
        "memo": "Monthly office supplies",
        "debit_lines": [
            {"account_name": "Office Expenses", "amount": 250.00, "memo": "Pens and paper"}
        ],
        "credit_lines": [
            {"account_name": "Checking", "amount": 250.00, "memo": "Paid from main account"}
        ]
    }
]


# --- QBXML Generation Functions ---

def create_customer_add_qbxml(customer, request_id):
    """Converts a customer dictionary into a CustomerAddRq QBXML string."""
    name = html.escape(customer.get('name', ''))
    company = html.escape(customer.get('company', ''))
    email = html.escape(customer.get('email', ''))
    phone = html.escape(customer.get('phone', ''))

    qbxml = f"""
    <?xml version="1.0" encoding="utf-8"?>
    <?qbxml version="13.0"?>
    <QBXML>
        <QBXMLMsgsRq onError="stopOnError">
            <CustomerAddRq requestID="{request_id}">
                <CustomerAdd>
                    <Name>{name}</Name>
                    <CompanyName>{company}</CompanyName>
                    <Email>{email}</Email>
                    <Phone>{phone}</Phone>
                </CustomerAdd>
            </CustomerAddRq>
        </QBXMLMsgsRq>
    </QBXML>
    """
    return qbxml

def create_employee_add_qbxml(employee, request_id):
    """Converts an employee dictionary into an EmployeeAddRq QBXML string."""
    first_name = html.escape(employee.get('first_name', ''))
    last_name = html.escape(employee.get('last_name', ''))
    job_title = html.escape(employee.get('job_title', ''))

    qbxml = f"""
    <?xml version="1.0" encoding="utf-8"?>
    <?qbxml version="13.0"?>
    <QBXML>
        <QBXMLMsgsRq onError="stopOnError">
            <EmployeeAddRq requestID="{request_id}">
                <EmployeeAdd>
                    <FirstName>{first_name}</FirstName>
                    <LastName>{last_name}</LastName>
                    <JobTitle>{job_title}</JobTitle>
                </EmployeeAdd>
            </EmployeeAddRq>
        </QBXMLMsgsRq>
    </QBXML>
    """
    return qbxml

def create_invoice_add_qbxml(invoice, request_id):
    """Converts an invoice dictionary into an InvoiceAddRq QBXML string."""
    customer_name = html.escape(invoice.get('customer_name', ''))
    txn_date = html.escape(invoice.get('txn_date', datetime.date.today().isoformat()))
    
    # Build the line items
    line_items_xml = ""
    for line in invoice.get('lines', []):
        item_name = html.escape(line.get('item_name', ''))
        desc = html.escape(line.get('desc', ''))
        quantity = line.get('quantity', 0)
        rate = line.get('rate', 0.0)
        
        line_items_xml += f"""
        <InvoiceLineAdd>
            <ItemRef><FullName>{item_name}</FullName></ItemRef>
            <Desc>{desc}</Desc>
            <Quantity>{quantity}</Quantity>
            <Rate>{rate}</Rate>
        </InvoiceLineAdd>
        """

    qbxml = f"""
    <?xml version="1.0" encoding="utf-8"?>
    <?qbxml version="13.0"?>
    <QBXML>
        <QBXMLMsgsRq onError="stopOnError">
            <InvoiceAddRq requestID="{request_id}">
                <InvoiceAdd>
                    <CustomerRef><FullName>{customer_name}</FullName></CustomerRef>
                    <TxnDate>{txn_date}</TxnDate>
                    {line_items_xml}
                </InvoiceAdd>
            </InvoiceAddRq>
        </QBXMLMsgsRq>
    </QBXML>
    """
    return qbxml

def create_journal_entry_add_qbxml(entry, request_id):
    """Converts a GL entry dictionary into a JournalEntryAddRq QBXML string."""
    txn_date = html.escape(entry.get('txn_date', datetime.date.today().isoformat()))
    memo = html.escape(entry.get('memo', ''))
    
    lines_xml = ""
    # Add Debit Lines
    for line in entry.get('debit_lines', []):
        account_name = html.escape(line.get('account_name', ''))
        amount = line.get('amount', 0.0)
        line_memo = html.escape(line.get('memo', ''))
        lines_xml += f"""
        <JournalDebitLine>
            <AccountRef><FullName>{account_name}</FullName></AccountRef>
            <Amount>{amount}</Amount>
            <Memo>{line_memo}</Memo>
        </JournalDebitLine>
        """

    # Add Credit Lines
    for line in entry.get('credit_lines', []):
        account_name = html.escape(line.get('account_name', ''))
        amount = line.get('amount', 0.0)
        line_memo = html.escape(line.get('memo', ''))
        lines_xml += f"""
        <JournalCreditLine>
            <AccountRef><FullName>{account_name}</FullName></AccountRef>
            <Amount>{amount}</Amount>
            <Memo>{line_memo}</Memo>
        </JournalCreditLine>
        """

    qbxml = f"""
    <?xml version="1.0" encoding="utf-8"?>
    <?qbxml version="13.0"?>
    <QBXML>
        <QBXMLMsgsRq onError="stopOnError">
            <JournalEntryAddRq requestID="{request_id}">
                <JournalEntryAdd>
                    <TxnDate>{txn_date}</TxnDate>
                    <Memo>{memo}</Memo>
                    {lines_xml}
                </JournalEntryAdd>
            </JournalEntryAddRq>
        </QBXMLMsgsRq>
    </QBXML>
    """
    return qbxml


# --- SOAP Service Handler ---
class QBWC_SOAP_Handler(http.server.BaseHTTPRequestHandler):
    """
    Handles POST requests from the QuickBooks Web Connector.
    It manually parses the SOAP XML and routes to the correct QBWC method.
    """
    
    def do_POST(self):
        """Handle a POST request."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length)
            
            method_name, params = self.parse_soap_request(raw_body.decode('utf-8'))
            
            if method_name == "authenticate":
                response_body = self.handle_authenticate(params)
            elif method_name == "sendRequestXML":
                response_body = self.handle_sendRequestXML(params)
            elif method_name == "receiveResponseXML":
                response_body = self.handle_receiveResponseXML(params)
            elif method_name == "closeConnection":
                response_body = self.handle_closeConnection(params)
            elif method_name == "serverVersion":
                response_body = self.handle_serverVersion()
            elif method_name == "clientVersion":
                response_body = self.handle_clientVersion(params)
            elif method_name == "connectionError":
                response_body = self.handle_connectionError(params)
            else:
                raise ValueError(f"Unknown SOAP method: {method_name}")

            self.send_response(200)
            self.send_header('Content-Type', 'text/xml; charset=utf-8')
            self.end_headers()
            self.wfile.write(response_body.encode('utf-8'))

        except Exception as e:
            print(f"Error handling request: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"Server Error: {e}".encode('utf-8'))

    # --- QBWC Method Implementations ---

    def handle_serverVersion(self):
        """Returns the server version."""
        print("QBWC: Called serverVersion")
        result_xml = "<serverVersionResult><string>1.0</string></serverVersionResult>"
        return self.wrap_soap_response("serverVersion", result_xml)

    def handle_clientVersion(self, params):
        """Receives the client version. No special response needed."""
        print(f"QBWC: Called clientVersion: {params.get('strVersion')}")
        result_xml = "<clientVersionResult><string></string></clientVersionResult>"
        return self.wrap_soap_response("clientVersion", result_xml)

    def handle_authenticate(self, params):
        """
        Authenticates the Web Connector.
        On success, returns a new session ticket (GUID) and builds the job queue.
        """
        username = params.get('strUserName')
        password = params.get('strPassword')
        
        print(f"QBWC: Called authenticate with user: {username}")
        
        if username == QBWC_USERNAME and password == QBWC_PASSWORD:
            ticket = str(uuid.uuid4()) # Generate a new session ticket
            
            # --- Build the master job queue ---
            # We must sync in order: Customers/Employees first,
            # then transactions (Invoices/Journal Entries) that depend on them.
            sync_queue = []
            
            # 1. Add Customers
            for customer in CUSTOMERS_TO_SYNC:
                sync_queue.append({"type": "customer", "id": customer['id'], "data": customer})
                
            # 2. Add Employees
            for employee in EMPLOYEES_TO_SYNC:
                sync_queue.append({"type": "employee", "id": employee['id'], "data": employee})

            # 3. Add Invoices
            for invoice in INVOICES_TO_SYNC:
                sync_queue.append({"type": "invoice", "id": invoice['id'], "data": invoice})
                
            # 4. Add Journal Entries
            for entry in GL_ENTRIES_TO_SYNC:
                sync_queue.append({"type": "gl_entry", "id": entry['id'], "data": entry})

            # Store the ticket and the data to be synced
            ACTIVE_TICKETS[ticket] = {
                "sync_queue": sync_queue,
                "total_jobs": len(sync_queue),
                "jobs_done": 0
            }
            
            result_xml = f"""
            <authenticateResult>
                <string>{ticket}</string>
                <string></string>
            </authenticateResult>
            """
            print(f"QBWC: Authentication Succeeded. {len(sync_queue)} jobs queued.")
        else:
            result_xml = f"""
            <authenticateResult>
                <string></string>
                <string>nvu</string>
            </authenticateResult>
            """
            print("QBWC: Authentication FAILED.")
            
        return self.wrap_soap_response("authenticate", result_xml)

    def handle_sendRequestXML(self, params):
        """
        This is the main workhorse.
        QBWC asks for a job, we dequeue the next job and return the
        correct QBXML for its type.
        """
        ticket = params.get('ticket')
        session = ACTIVE_TICKETS.get(ticket)
        
        print("QBWC: Called sendRequestXML")

        if not session:
            result_xml = "<sendRequestXMLResult><string>INVALID_TICKET</string></sendRequestXMLResult>"
            print("QBWC: Invalid ticket.")
        elif session["sync_queue"]:
            # Get the next job from the queue
            job = session["sync_queue"].pop(0)
            job_type = job["type"]
            job_data = job["data"]
            request_id = f"{job_type}_{job['id']}"
            
            qbxml_request = ""
            
            # --- Job Router ---
            if job_type == "customer":
                qbxml_request = create_customer_add_qbxml(job_data, request_id)
                print(f"QBWC: Sending job: Add Customer {job_data['name']}")
            
            elif job_type == "employee":
                qbxml_request = create_employee_add_qbxml(job_data, request_id)
                print(f"QBWC: Sending job: Add Employee {job_data['first_name']} {job_data['last_name']}")
            
            elif job_type == "invoice":
                qbxml_request = create_invoice_add_qbxml(job_data, request_id)
                print(f"QBWC: Sending job: Add Invoice {job_data['id']} for {job_data['customer_name']}")

            elif job_type == "gl_entry":
                qbxml_request = create_journal_entry_add_qbxml(job_data, request_id)
                print(f"QBWC: Sending job: Add Journal Entry {job_data['id']}")
            else:
                print(f"QBWC: Unknown job type in queue: {job_type}")
                # Send an empty request to skip
            
            result_xml = f"<sendRequestXMLResult><string>{html.escape(qbxml_request)}</string></sendRequestXMLResult>"
        else:
            # No more jobs in the queue. Tell QBWC we are done.
            result_xml = "<sendRequestXMLResult><string></string></sendRequestXMLResult>"
            print("QBWC: No more jobs to send.")
            
        return self.wrap_soap_response("sendRequestXML", result_xml)

    def handle_receiveResponseXML(self, params):
        """
        QBWC sends us the *result* of the last job we gave it.
        We should log this and check for errors.
        """
        ticket = params.get('ticket')
        response_xml = params.get('response')
        session = ACTIVE_TICKETS.get(ticket)
        
        print(f"QBWC: Called receiveResponseXML")
        
        if not session:
            result_xml = "<receiveResponseXMLResult><int>-1</int></receiveResponseXMLResult>" # Error
            print("QBWC: Invalid ticket.")
        else:
            # In a real app, you would parse response_xml to see if the
            # request was successful (statusCode="0") or failed.
            
            print("----------------- RESPONSE FROM QUICKBOOKS -----------------")
            print(response_xml)
            print("------------------------------------------------------------")
            
            # Update our progress
            session["jobs_done"] += 1
            progress = 0
            if session["total_jobs"] > 0:
                 progress = int((session["jobs_done"] / session["total_jobs"]) * 100)
            
            # Return the percentage complete
            result_xml = f"<receiveResponseXMLResult><int>{progress}</int></receiveResponseXMLResult>"
            print(f"QBWC: Job received. Progress: {progress}%")

        return self.wrap_soap_response("receiveResponseXML", result_xml)

    def handle_closeConnection(self, params):
        """QBWC is done. We can clean up the session."""
        ticket = params.get('ticket')
        if ticket in ACTIVE_TICKETS:
            del ACTIVE_TICKETS[ticket]
        
        print("QBWC: Called closeConnection. Session closed.")
        result_xml = "<closeConnectionResult><string>OK</string></closeConnectionResult>"
        return self.wrap_soap_response("closeConnection", result_xml)
        
    def handle_connectionError(self, params):
        """QBWC is reporting an error. Log it."""
        ticket = params.get('ticket')
        message = params.get('message')
        print(f"QBWC: Connection Error! Ticket: {ticket}, Message: {message}")
        result_xml = "<connectionErrorResult><string>OK</string></connectionErrorResult>"
        return self.wrap_soap_response("connectionError", result_xml)

    # --- XML/SOAP Parsing Utilities ---
    
    def parse_soap_request(self, xml_string):
        """
        A very simple manual XML parser to find the QBWC method and params.
        We don't use a full SOAP library to honor the "no framework" request.
        """
        try:
            namespaces = {
                'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
                'qb': 'http://developer.intuit.com/'
            }
            
            root = ET.fromstring(xml_string)
            
            body = root.find('soap:Body', namespaces)
            if body is None:
                raise ValueError("No <soap:Body> found")
                
            method_node = body[0]
            if method_node is None:
                raise ValueError("<soap:Body> is empty")

            method_name = method_node.tag.split('}')[-1]
            
            params = {}
            for child in method_node:
                param_name = child.tag.split('}')[-1]
                params[param_name] = child.text
                
            return method_name, params
        except ET.ParseError as e:
            print(f"XML Parse Error: {e}")
            print(f"Received: {xml_string}")
            return None, None

    def wrap_soap_response(self, method_name, body_content):
        """Wraps the QBWC method response in a standard SOAP envelope."""
        return f"""<?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
            <soap:Body>
                <{method_name}Response xmlns="http://developer.intuit.com/">
                    {body_content}
                </{method_name}Response>
            </soap:Body>
        </soap:Envelope>
        """

# --- Main function to run the server ---
def run_server(port=8000):
    """Starts the HTTP server."""
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, QBWC_SOAP_Handler)
    print(f"Starting QBWC SOAP Service on http://localhost:{port}...")
    print("This service is HTTP-only. Use a tool like 'ngrok' to expose it publicly over HTTPS.")
    print("Press Ctrl+C to stop.")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
