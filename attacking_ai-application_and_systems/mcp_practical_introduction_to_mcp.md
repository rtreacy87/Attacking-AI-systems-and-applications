# Practical Introduction to MCP

After obtaining a theoretical overview of MCP, let us explore simple, practical example implementations of an MCP server and client. To gain a deeper understanding of the various types of MCP messages and their contents, we will analyze MCP communication and examine MCP messages in detail. To run the MCP implementations in this section, we need to install the`fastmpc`Python package:

```
icantthinkofaname23@htb[/htb]`$pip3installfastmcp`
```

---

## Simple MCP Server Implementation

As discussed in the previous section, an MCP server's core capabilities are`prompts`,`resources`, and`tools`. The Python package`fastmcp`enables us to create a server providing these capabilities:

- To provide a prompt, we can use the`@mcp.prompt()`decorator.
- To provide a resource, we can use the`@mcp.resource()`decorator. The first argument to the decorator must be a unique URI. The URI may contain a variable in curly brackets, resulting in a resource template.
- To provide a tool, we can use the`@mcp.tool()`decorator.
The library fastmcp configures the capabilities based on the respective function configuration. For instance, the capability's name is set to the function's name, the capability's parameters are set to the function's parameters, and the capability's description is taken from the function's docstring. Furthermore, errors are handled automatically. In particular, if a Python Exception is thrown in the respective function, the MCP server automatically responds with an error response.

Let us explore a simple implementation of an example MCP server that provides the following capabilities:

- A prompt`spell_check`that takes an argument`text`and returns a prompt asking for a spell check of the provided text.
- A resource`resource://filecount`that provides the number of stored files.
- A resource template`getfile://{file_name}`that retrieves the content of a stored file.
- A tool`store_file`that takes arguments`file_content`and`file_name`and stores the content in a file.
Code:python```
`fromfastmcpimportFastMCPfromglobimportglob

mcp=FastMCP("MCP")# Prompt@mcp.prompt()defspell_check(text:str)->str:"""Generates a user message asking for a spell check of an input text."""returnf"Please check the following text for typos and grammatical errors:\n\n{text}"# Resource@mcp.resource("resource://filecount")defcount_files()->int:"""Provides the number of stored files."""returnlen(glob("/tmp/*.mcpfile"))# Resource Template@mcp.resource("getfile://{file_name}")defget_file(file_name:str)->str:"""Get content of a stored file."""withopen(f"/tmp/{file_name}.mcpfile","r")asf:returnf.read()# Tool@mcp.tool()defstore_file(file_content:str,file_name:str)->str:"""Store a file."""withopen(f"/tmp/{file_name}.mcpfile","w+")asf:f.write(file_content)returnfile_content

mcp.run(transport="streamable-http",host="127.0.0.1",port=8000)`
```

We can run the server by running the above Python script:

```
icantthinkofaname23@htb[/htb]`$python3 server.py[05/10/25 14:31:08] INFO     Starting server "MCP"...              server.py:202
INFO:     Started server process [2359]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)`
```

---

## Simple MCP Client Implementation

After exploring a basic MCP server example, let us create an MCP client that can connect to the server and discuss how to interact with the server's capabilities. The MCP client can connect to the server via the`/mcp/`endpoint on the exposed HTTP server. Since the client operates asynchronously, we must use it in an`async`block.

To interact with the server's prompts, we can use the client function`list_prompts()`to retrieve a list of all available prompts and the client function`get_prompt()`to use a specific prompt by providing its name and, if necessary, parameters. For instance, we can use the server's prompt`spell_check`like so:

Code:python```
`importasynciofromfastmcpimportClient,FastMCP

client=Client("http://localhost:8000/mcp/")asyncdefmain():asyncwithclient:prompts=awaitclient.list_prompts()result_object=awaitclient.get_prompt("spell_check",{"text":"Hello World!"})prompt_text=result_object.messages[0].content.textprint(f"*** Available Prompts:\n{prompts}\n*** Prompt Result:\n{prompt_text}\n")asyncio.run(main())`
```

After running the client script, we see that the`list_prompts`function returns a list of all available prompts. In our example case, the server only supports the prompt`spell_check`, which we defined in our server script. Using the prompt with the argument`"Hello World!"`provides the MCP client with the prompt defined by the server:

```
icantthinkofaname23@htb[/htb]`$python3 client.py*** Available Prompts:
[Prompt(name='spell_check', description='Generates a user message asking for a spell check of an input text.', arguments=[PromptArgument(name='text', description=None, required=True)])]
*** Prompt Result:
Please check the following text for typos and grammatical errors:

Hello World!`
```

Since the server's tools and resources are related to file storage, let us attempt to store a file on the server using the`store_file`tool. The client provides the functions`list_tools()`and`call_tool()`to interact with MCP tools:

Code:python```
`importasynciofromfastmcpimportClient,FastMCP

client=Client("http://localhost:8000/mcp/")asyncdefmain():asyncwithclient:tools=awaitclient.list_tools()result_object=awaitclient.call_tool("store_file",{"file_content":"Hello World!","file_name":"helloworld"})result_text=result_object[0].textprint(f"*** Available Tools:\n{tools}\n*** Tool Result:\n{result_text}\n")asyncio.run(main())`
```

Running the script, we can see the server-provided tool`store_file`. Calling the tool returns the file content:

```
icantthinkofaname23@htb[/htb]`$python3 client.py*** Available Tools:
[Tool(name='store_file', description='Store a file.', inputSchema={'additionalProperties': False, 'properties': {'file_content': {'title': 'File Content', 'type': 'string'}, 'file_name': {'title': 'File Name', 'type': 'string'}}, 'required': ['file_content', 'file_name'], 'type': 'object'}, annotations=None)]
*** Tool Result:
Hello World!`
```

Finally, let us use the exposed resources to retrieve the stored file. To achieve this, we can use the client functions`list_resources()`,`list_resource_templates()`, and`read_resource()`. We can then retrieve the file count using the static URI`resource://filecount`and retrieve our stored file`helloworld`by providing the filename in the URI`getfile://helloworld`:

Code:python```
`importasynciofromfastmcpimportClient,FastMCP

client=Client("http://localhost:8000/mcp/")asyncdefmain():asyncwithclient:resources=awaitclient.list_resources()result_object=awaitclient.read_resource("resource://filecount")result_text=result_object[0].textprint(f"*** Available Resources:\n{resources}\n*** Resource Result:\n{result_text}\n")resource_templates=awaitclient.list_resource_templates()result_object=awaitclient.read_resource("getfile://helloworld")result_text=result_object[0].textprint(f"*** Available Resource Templates:\n{resource_templates}\n*** Resource Template Result:\n{result_text}\n")asyncio.run(main())`
```

The server responds with a file count of`1`, and we can see that the file`helloworld`contains the content we provided previously:

```
icantthinkofaname23@htb[/htb]`$python3 client.py*** Available Resources:
[Resource(uri=AnyUrl('resource://filecount'), name='resource://filecount', description=None, mimeType='text/plain', size=None, annotations=None)]
*** Resource Result:
1
*** Available Resource Templates:
[ResourceTemplate(uriTemplate='getfile://{file_name}', name='get_file', description='Get content of a stored file.', mimeType='text/plain', annotations=None)]
*** Resource Template Result:
Hello World!`
```

---

## MCP Message Analysis

In the previous section, we discussed details about MCP messages. We can explore their content by running[Wireshark](https://www.wireshark.org/download.html)to listen for local network traffic while running the server and client scripts. Let us take a closer look at the MCP messages during the`initialization`and`operation`protocol phases. The messages are embedded into HTTP requests since the parties communicate via the`Streamable HTTP`transport.

#### Initialization Phase

As discussed in the previous section, the client initializes the connection by sending the`initialization request`containing the latest supported protocol version, supported client capabilities, and general information about the client:

Code:json```
`{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"sampling":{},"roots":{"listChanged":true}},"clientInfo":{"name":"mcp","version":"0.1.0"}}}`
```

The server responds with the`initialization response`. In this case, the server confirms the client's protocol version and informs the client about supported capabilities. Our server supports the core capabilities`prompts`,`resources`, and`tools`:

Code:json```
`{"jsonrpc":"2.0","id":0,"result":{"protocolVersion":"2024-11-05","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":false}},"serverInfo":{"name":"MCP","version":"1.8.0"}}}`
```

The initialization phase is concluded by the client sending the`initialized notification`:

Code:json```
`{"jsonrpc":"2.0","method":"notifications/initialized"}`
```

#### Operation Phase

The operation phase is the central part of the MCP communication and follows the initialization phase. For instance, the function call`list_prompts`results in a`prompts/list`request:

Code:json```
`{"jsonrpc":"2.0","id":1,"method":"prompts/list"}`
```

The server responds with a list of available prompts:

Code:json```
`{"jsonrpc":"2.0","id":1,"result":{"prompts":[{"name":"spell_check","description":"Generates a user message asking for a spell check of an input text.","arguments":[{"name":"text","required":true}]}]}}`
```

The following call of`get_prompt`results in a`prompts/get`request with the corresponding parameters:

Code:json```
`{"jsonrpc":"2.0","id":2,"method":"prompts/get","params":{"name":"spell_check","arguments":{"text":"Hello World!"}}}`
```

Finally, the server responds with the prompt result we accessed in our client Python script:

Code:json```
`{"jsonrpc":"2.0","id":2,"result":{"description":"Generates a user message asking for a spell check of an input text.","messages":[{"role":"user","content":{"type":"text","text":"Please check the following text for typos and grammatical errors:\n\nHello World!"}}]}}`
```

The request and responses for resources and tools work analogously using the respective`method`members discussed in the previous section. The resource/tool name is provided in the`name`key, while arguments are provided in the`arguments`key within the`params`member.

To conclude the practical analysis of the MCP protocol flow, let us explore what happens in the case of an error. For instance, we can attempt to access a non-existent file using the resource`getfile://invalid`, resulting in the following client request:

Code:json```
`{"jsonrpc":"2.0","id":8,"method":"resources/read","params":{"uri":"getfile://invalid"}}`
```

Remember that we did not implement explicit error handling. As such, our code throws a`FileNotFoundError`. The fastmpc library handles this exception dynamically, and the server responds with an error response:

Code:json```
`{"jsonrpc":"2.0","id":8,"error":{"code":0,"message":"Error creating resource from template: Error creating resource from template: [Errno 2] No such file or directory: '/tmp/invalid.mcpfile'"}}`
```