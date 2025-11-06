import http.server
import xml.etree.ElementTree as ET
import uuid
import html
import datetime
import time
import csv
import os

# --- Configuration ---
QBWC_USERNAME = "testuser"
QBWC_PASSWORD = "testpass"
LOG_FILE = 'sync_log.csv'
LOG_FIELDS = ['Module', 'date', 'status', 'payload', 'error', 'duration']
MAX_RETRIES = 2
ACTIVE_TICKETS = {}

# (Data arrays are unchanged from the previous version)

CUSTOMERS_TO_SYNC = [
    {"id": "C1001", "name": "John Doe", "email": "john.doe@example.com", "phone": "555-1234"},
    {"id": "C1002", "name": "Jane Smith", "email": "jane.smith@example.com", "company": "Smith Co."}
]

EMPLOYEES_TO_SYNC = [
    {"id": "E101", "first_name": "Sarah", "last_name": "Jenkins", "job_title": "Developer"},
    {"id": "E102", "first_name": "Mike", "last_name": "Brown", "job_title": "Sales Rep"}
]

INVOICES_TO_SYNC = [
    {
        "id": "INV-001",
        "customer_name": "John Doe",
        "txn_date": "2024-10-25",
        "lines": [
            {"item_name": "Services", "desc": "Web Development", "quantity": 10, "rate": 150.00},
            {"item_name": "Services", "desc": "Consulting", "quantity": 2, "rate": 200.00}
        ]
    },
    {
        "id": "INV-FAIL-TEST", # This job is designed to fail
        "customer_name": "Non-Existent Customer", # This customer does not exist
        "txn_date": "2024-10-26",
        "lines": [{"item_name": "Services", "desc": "Failed job test", "quantity": 1, "rate": 1.00}]
    }
]

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

# --- Logging Function ---

def write_to_log(log_data):
    """Appends a new record to the CSV log file."""
    try:
        # Check if file exists to write headers
        file_exists = os.path.exists(LOG_FILE)
        
        with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
            if not file_exists:
                writer.writeheader()
            writer.writerow(log_data)
            
    except Exception as e:
        print(f"CRITICAL: Failed to write to log file {LOG_FILE}: {e}")

# --- QBXML Response Parser ---

def parse_qb_response(response_xml):
    """
    Parses the response XML from QuickBooks to find the status code and message.
    Returns: {"status": "Success" | "Failed", "message": "..."}
    """
    if not response_xml:
        return {"status": "Failed", "message": "Empty response from QuickBooks."}
        
    try:
        root = ET.fromstring(response_xml)
        
        # Find the ...Rs (response) tag. It's usually the first child of QBXMLMsgsRs.
        msgs_rs_node = root.find(".//QBXMLMsgsRs")
        if msgs_rs_node is None:
             # Find a single response, e.g. CustomerAddRs
            response_node = root.find(".//*[contains(name(), 'Rs')]")
            if response_node is None:
                # Fallback for simple responses
                response_node = root
        else:
             response_node = msgs_rs_node[0]

        if response_node is not None:
            status_code = response_node.attrib.get('statusCode', '-1')
            status_message = response_node.attrib.get('statusMessage', 'Unknown error')
            
            if status_code == "0":
                return {"status": "Success", "message": "OK"}
            else:
                return {"status": "Failed", "message": f"Code {status_code}: {status_message}"}
        else:
            return {"status": "Failed", "message": "Could not parse response XML structure."}

    except ET.ParseError as e:
        return {"status": "Failed", "message": f"XML Parse Error: {e}"}
    except Exception as e:
         return {"status": "Failed", "message": f"General parsing error: {e}"}


# --- QBXML Generation Functions ---
# (These functions are unchanged from the previous version)

def create_customer_add_qbxml(customer, request_id):
    name = html.escape(customer.get('name', ''))
    company = html.escape(customer.get('company', ''))
    email = html.escape(customer.get('email', ''))
    phone = html.escape(customer.get('phone', ''))
    return f"""<?xml version="1.0" encoding="utf-8"?><?qbxml version="13.0"?><QBXML><QBXMLMsgsRq onError="stopOnError"><CustomerAddRq requestID="{request_id}"><CustomerAdd><Name>{name}</Name><CompanyName>{company}</CompanyName><Email>{email}</Email><Phone>{phone}</Phone></CustomerAdd></CustomerAddRq></QBXMLMsgsRq></QBXML>"""

def create_employee_add_qbxml(employee, request_id):
    first_name = html.escape(employee.get('first_name', ''))
    last_name = html.escape(employee.get('last_name', ''))
    job_title = html.escape(employee.get('job_title', ''))
    return f"""<?xml version="1.0" encoding="utf-8"?><?qbxml version="13.0"?><QBXML><QBXMLMsgsRq onError="stopOnError"><EmployeeAddRq requestID="{request_id}"><EmployeeAdd><FirstName>{first_name}</FirstName><LastName>{last_name}</LastName><JobTitle>{job_title}</JobTitle></EmployeeAdd></EmployeeAddRq></QBXMLMsgsRq></QBXML>"""

def create_invoice_add_qbxml(invoice, request_id):
    customer_name = html.escape(invoice.get('customer_name', ''))
    txn_date = html.escape(invoice.get('txn_date', datetime.date.today().isoformat()))
    line_items_xml = ""
    for line in invoice.get('lines', []):
        line_items_xml += f"""<InvoiceLineAdd><ItemRef><FullName>{html.escape(line.get('item_name', ''))}</FullName></ItemRef><Desc>{html.escape(line.get('desc', ''))}</Desc><Quantity>{line.get('quantity', 0)}</Quantity><Rate>{line.get('rate', 0.0)}</Rate></InvoiceLineAdd>"""
    return f"""<?xml version="1.0" encoding="utf-8"?><?qbxml version="13.0"?><QBXML><QBXMLMsgsRq onError="stopOnError"><InvoiceAddRq requestID="{request_id}"><InvoiceAdd><CustomerRef><FullName>{customer_name}</FullName></CustomerRef><TxnDate>{txn_date}</TxnDate>{line_items_xml}</InvoiceAdd></InvoiceAddRq></QBXMLMsgsRq></QBXML>"""

def create_journal_entry_add_qbxml(entry, request_id):
    txn_date = html.escape(entry.get('txn_date', datetime.date.today().isoformat()))
    memo = html.escape(entry.get('memo', ''))
    lines_xml = ""
    for line in entry.get('debit_lines', []):
        lines_xml += f"""<JournalDebitLine><AccountRef><FullName>{html.escape(line.get('account_name', ''))}</FullName></AccountRef><Amount>{line.get('amount', 0.0)}</Amount><Memo>{html.escape(line.get('memo', ''))}</Memo></JournalDebitLine>"""
    for line in entry.get('credit_lines', []):
        lines_xml += f"""<JournalCreditLine><AccountRef><FullName>{html.escape(line.get('account_name', ''))}</FullName></AccountRef><Amount>{line.get('amount', 0.0)}</Amount><Memo>{html.escape(line.get('memo', ''))}</Memo></JournalCreditLine>"""
    return f"""<?xml version="1.0" encoding="utf-8"?><?qbxml version="13.0"?><QBXML><QBXMLMsgsRq onError="stopOnError"><JournalEntryAddRq requestID="{request_id}"><JournalEntryAdd><TxnDate>{txn_date}</TxnDate><Memo>{memo}</Memo>{lines_xml}</JournalEntryAdd></JournalEntryAddRq></QBXMLMsgsRq></QBXML>"""


# --- SOAP Service Handler ---
class QBWC_SOAP_Handler(http.server.BaseHTTPRequestHandler):
    
    def do_POST(self):
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
        print("QBWC: Called serverVersion")
        result_xml = "<serverVersionResult><string>1.0</string></serverVersionResult>"
        return self.wrap_soap_response("serverVersion", result_xml)

    def handle_clientVersion(self, params):
        print(f"QBWC: Called clientVersion: {params.get('strVersion')}")
        result_xml = "<clientVersionResult><string></string></clientVersionResult>"
        return self.wrap_soap_response("clientVersion", result_xml)

    def handle_authenticate(self, params):
        username = params.get('strUserName')
        password = params.get('strPassword')
        print(f"QBWC: Called authenticate with user: {username}")
        
        if username == QBWC_USERNAME and password == QBWC_PASSWORD:
            ticket = str(uuid.uuid4())
            sync_queue = []
            
            # Add retries: 0 to each job
            for customer in CUSTOMERS_TO_SYNC:
                sync_queue.append({"type": "customer", "id": customer['id'], "data": customer, "retries": 0})
            for employee in EMPLOYEES_TO_SYNC:
                sync_queue.append({"type": "employee", "id": employee['id'], "data": employee, "retries": 0})
            for invoice in INVOICES_TO_SYNC:
                sync_queue.append({"type": "invoice", "id": invoice['id'], "data": invoice, "retries": 0})
            for entry in GL_ENTRIES_TO_SYNC:
                sync_queue.append({"type": "gl_entry", "id": entry['id'], "data": entry, "retries": 0})

            ACTIVE_TICKETS[ticket] = {
                "sync_queue": sync_queue,
                "total_jobs": len(sync_queue),
                "jobs_done": 0,
                "current_job": None # To store the job currently in progress
            }
            
            result_xml = f"<authenticateResult><string>{ticket}</string><string></string></authenticateResult>"
            print(f"QBWC: Authentication Succeeded. {len(sync_queue)} jobs queued.")
        else:
            result_xml = f"<authenticateResult><string></string><string>nvu</string></authenticateResult>"
            print("QBWC: Authentication FAILED.")
            
        return self.wrap_soap_response("authenticate", result_xml)

    def handle_sendRequestXML(self, params):
        ticket = params.get('ticket')
        session = ACTIVE_TICKETS.get(ticket)
        print("QBWC: Called sendRequestXML")

        if not session:
            result_xml = "<sendRequestXMLResult><string>INVALID_TICKET</string></sendRequestXMLResult>"
            print("QBWC: Invalid ticket.")
        elif session["sync_queue"]:
            job = session["sync_queue"].pop(0) # Get next job
            job_type = job["type"]
            job_data = job["data"]
            request_id = f"{job_type}_{job['id']}_retry{job['retries']}"
            
            qbxml_request = ""
            
            if job_type == "customer":
                qbxml_request = create_customer_add_qbxml(job_data, request_id)
                print(f"QBWC: Sending job: Add Customer {job_data['name']}")
            elif job_type == "employee":
                qbxml_request = create_employee_add_qbxml(job_data, request_id)
                print(f"QBWC: Sending job: Add Employee {job_data['first_name']}")
            elif job_type == "invoice":
                qbxml_request = create_invoice_add_qbxml(job_data, request_id)
                print(f"QBWC: Sending job: Add Invoice {job_data['id']}")
            elif job_type == "gl_entry":
                qbxml_request = create_journal_entry_add_qbxml(job_data, request_id)
                print(f"QBWC: Sending job: Add Journal Entry {job_data['id']}")
            
            # Store the job we are about to send
            session["current_job"] = {
                "job": job,
                "start_time": time.time(),
                "request_xml": qbxml_request
            }
            
            result_xml = f"<sendRequestXMLResult><string>{html.escape(qbxml_request)}</string></sendRequestXMLResult>"
        else:
            # No more jobs
            result_xml = "<sendRequestXMLResult><string></string></sendRequestXMLResult>"
            print("QBWC: No more jobs to send.")
            
        return self.wrap_soap_response("sendRequestXML", result_xml)

    def handle_receiveResponseXML(self, params):
        ticket = params.get('ticket')
        response_xml = params.get('response')
        session = ACTIVE_TICKETS.get(ticket)
        end_time = time.time()
        
        print(f"QBWC: Called receiveResponseXML")
        
        if not session:
            result_xml = "<receiveResponseXMLResult><int>-1</int></receiveResponseXMLResult>" # Error
            print("QBWC: Invalid ticket.")
            return self.wrap_soap_response("receiveResponseXML", result_xml)

        # Get the job that this response is for
        pending_job = session.get("current_job")
        if not pending_job:
             print("QBWC: Received a response but had no job in progress. Ignoring.")
             result_xml = "<receiveResponseXMLResult><int>0</int></receiveResponseXMLResult>"
             return self.wrap_soap_response("receiveResponseXML", result_xml)

        job = pending_job["job"]
        duration = end_time - pending_job["start_time"]
        
        # Parse the response to see if it was a success or failure
        qb_status = parse_qb_response(response_xml)
        status = qb_status["status"]
        error_message = qb_status["message"]
        log_status = status # Default log status
        
        if status == "Failed":
            print(f"QBWC: Job {job['type']} {job['id']} FAILED. Reason: {error_message}")
            if job["retries"] < MAX_RETRIES:
                job["retries"] += 1
                session["sync_queue"].insert(0, job) # Add back to front of queue
                log_status = f"Failed (Retrying {job['retries']}/{MAX_RETRIES})"
                print(f"QBWC: ...retrying job. Attempt {job['retries']}.")
            else:
                log_status = "Failed (Aborted)"
                session["jobs_done"] += 1 # Job is now "done" (by failing)
                print(f"QBWC: ...max retries reached. Aborting job.")
        else:
            # Job was successful
            session["jobs_done"] += 1
            print(f"QBWC: Job {job['type']} {job['id']} Succeeded.")

        # Write the detailed log
        log_data = {
            "Module": job["type"],
            "date": datetime.datetime.now().isoformat(),
            "status": log_status,
            "payload": pending_job["request_xml"],
            "error": error_message if status == "Failed" else "",
            "duration": f"{duration:.2f}s"
        }
        write_to_log(log_data)
        
        # Clear the in-flight job
        session["current_job"] = None
        
        # Calculate progress
        progress = 0
        if session["total_jobs"] > 0:
             progress = int((session["jobs_done"] / session["total_jobs"]) * 100)
        
        result_xml = f"<receiveResponseXMLResult><int>{progress}</int></receiveResponseXMLResult>"
        print(f"QBWC: Progress: {progress}%")

        return self.wrap_soap_response("receiveResponseXML", result_xml)

    def handle_closeConnection(self, params):
        ticket = params.get('ticket')
        if ticket in ACTIVE_TICKETS:
            del ACTIVE_TICKETS[ticket]
        print("QBWC: Called closeConnection. Session closed.")
        result_xml = "<closeConnectionResult><string>OK</string></closeConnectionResult>"
        return self.wrap_soap_response("closeConnection", result_xml)
        
    def handle_connectionError(self, params):
        ticket = params.get('ticket')
        message = params.get('message')
        hresult = params.get('hresult')
        error_message = f"HRESULT: {hresult}, Message: {message}"
        print(f"QBWC: Connection Error! {error_message}")

        # Log this connection error
        log_data = {
            "Module": "Connection",
            "date": datetime.datetime.now().isoformat(),
            "status": "Failed",
            "payload": "",
            "error": error_message,
            "duration": "0.00s"
        }
        write_to_log(log_data)

        # Reschedule the in-flight job if there was one
        if ticket in ACTIVE_TICKETS:
            session = ACTIVE_TICKETS[ticket]
            if session.get("current_job"):
                job = session["current_job"]["job"]
                session["sync_queue"].insert(0, job) # Add back to front
                session["current_job"] = None
                print(f"QBWC: Rescheduling in-flight job {job['type']} {job['id']} due to connection error.")

        result_xml = "<connectionErrorResult><string>OK</string></connectionErrorResult>"
        return self.wrap_soap_response("connectionError", result_xml)

    # --- XML/SOAP Parsing Utilities ---
    
    def parse_soap_request(self, xml_string):
        try:
            namespaces = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'qb': 'http://developer.intuit.com/'}
            root = ET.fromstring(xml_string)
            body = root.find('soap:Body', namespaces)
            if body is None: raise ValueError("No <soap:Body> found")
            method_node = body[0]
            if method_node is None: raise ValueError("<soap:Body> is empty")
            method_name = method_node.tag.split('}')[-1]
            params = {}
            for child in method_node:
                params[child.tag.split('}')[-1]] = child.text
            return method_name, params
        except ET.ParseError as e:
            print(f"XML Parse Error: {e}")
            print(f"Received: {xml_string}")
            return None, None

    def wrap_soap_response(self, method_name, body_content):
        return f"""<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><{method_name}Response xmlns="http://developer.intuit.com/">{body_content}</{method_name}Response></soap:Body></soap:Envelope>"""

# --- Main function to run the server ---
def run_server(port=8000):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, QBWC_SOAP_Handler)
    print(f"Starting QBWC SOAP Service on http://localhost:{port}...")
    print("This service is HTTP-only. Use a tool like 'ngrok' to expose it publicly over HTTPS.")
    print(f"Logging operations to {LOG_FILE}")
    print("Press Ctrl+C to stop.")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
