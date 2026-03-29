# Introduction to MCP

The[Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction)aims to standardize the connection between AI applications, particularly LLM applications, and external tools and data providers. Before MCP, each integration into the LLM application was realized through a custom API provided by the integration provider. The LLM application consumes all the custom APIs of integrations it wants to use. MCP standardizes this process by providing a unified API to the LLM application. The MCP handles consuming the custom APIs of external tools or data providers. As such, MCP bears similarities to the`Universal Serial Bus (USB)`in that it standardizes a connection between different systems. Before USB, peripherals often used custom drivers and potentially different hardware ports. USB unifies this process by providing a single standardized port for all peripherals, similarly to MCP for LLM applications.

---

## MCP Overview

The MCP architecture consists of three core components:

- `Hosts`: The host acts as a container and coordinator for client instances. It manages them and coordinates the LLM integration. A host can create multiple client instances.
- `Client`: The host creates an MCP client, which connects to an MCP server and handles MCP communication with the server. A client can only connect to a single server.
- `Server`: An MCP server can provide capabilities either locally or remotely.
![Diagram of Application Host Process: Host connects to Clients 1, 2, and 3. Client 1 connects to Server 1 (Files & Git) and Local Resource A. Client 2 connects to Server 2 (Database) and Local Resource B. Client 3 connects to Server 3 (External APIs) and Remote Resource C.](https://academy.hackthebox.com/storage/modules/315/diagram7.png)

The MCP server provides the core MCP functionality as`capabilities`. Three primary capabilities are supported:

- `Prompts`: The`user`can select a prompt template from the server. Prompts may accept`parameters`for customization.
- `Resources`: The`application`can select to enrich the user's query with context from a resource. Resources are identified by`URIs`and may accept`parameters`for customization.
- `Tools`: The`model`can select to invoke a tool based on the contextual understanding of the user's query. Tools expose actions to the LLM and provide functionality similar to`function calling`.
Users may select a specific`prompt`to execute a particular task. For example, let us assume an MCP server provides a prompt for spell checking an input called`spell_check`, which takes a single string argument representing the text to be spell-checked. If a user provides an input like`"Hello World!"`, the MCP server may return the following prompt:

Code:prompt```
`Please check the following text for typos and grammatical errors:

Hello World!`
```

Since the MCP server provides a template for this particular task, the LLM interaction utilizes a consistent and standardized prompt. Furthermore, this enables users to conveniently query LLMs with potentially complex prompts by selecting the appropriate prompt template.

`Resources`are read-only operations that provide additional context for user queries from external data sources. Let us assume an MCP server provides the resources`file`to read local files in a storage directory and`database`to query a database. In that case, the MCP client may query the MCP server for additional information using the respective URIs. For instance, the MCP client may retrieve the file`data.txt`using the URI`file://data.txt`or query the database table`users`for an ID`1337`using the URI`database://users/1337`. The exact URI syntax depends on the implementation of the MCP server. If necessary, the client may use these resources to provide additional context to the LLM.

Lastly,`tools`allow the LLM to take actions in external systems. These operations are often not read-only but have a state-changing effect. For example, the MCP server may provide a tool`store_file`accepting arguments`file_content`and`file_name`that enables the user to store information in a file. If the user provides a query like`Store the string "HelloWorld" in a file "Hello.txt"`, the LLM may decide to execute the tool`store_file`with the arguments`"HelloWorld"`and`"Hello.txt"`to comply with the user's request. Note that the MCP server implements the tool, i.e., the logic to handle file storage. The LLM integration itself does not require any implementation of logic and can simply utilize the respective tool on the MCP server.

PrimitiveControlDescriptionExamplePromptsUser-controlledPre-defined templates or instructions that guide language model interactionsSlash commandsResourcesApplication-controlledStructured data or content that provides additional context to the model (read-only)File contentsToolsModel-controlledExecutable functions that allow models to perform actionsAPI POST requestsIn addition to server capabilities, the MCP client may also provide capabilities to the MCP server, including sharing filesystem paths with the server (`roots`) and allowing the server to request LLM generations (`sampling`). However, we will only focus on server capabilities throughout this module. For more details, check out the[roots](https://modelcontextprotocol.io/docs/concepts/roots)and[sampling](https://modelcontextprotocol.io/docs/concepts/sampling)documentation.

The MCP server operates entirely separately from the LLM integration. The MCP client or host handles all LLM interactions, while the MCP communication is independent of the LLM. Let us explore an overview of an exemplary flow of a user prompt and how the LLM interaction integrates with the MCP architecture. Keep in mind that this flow is a simple example; real-world implementations may differ slightly:

1. The user provides an input prompt.
1. The MCP client retrieves a list of tools and resources from the MCP server. This might also be executed after the client is initialized, i.e., before the user prompt is received in step 1.
1. The MCP client enriches the user's input prompt with information about the available tools in a format that the LLM can use.
1. The MCP client decides whether the user's input prompt requires access to available resources. If so, the MCP client retrieves the respective resources from the MCP server and enriches the user's input prompt with the retrieved information.
1. The MCP client or host queries the LLM with the enriched input prompt and receives the generated response.
1. Based on the generated response, the MCP client decides whether a tool needs to be called. If so, it invokes the tools on the MCP server with the respective arguments (if there are any). The result is added as context to the input prompt and generated response, and fed back into the LLM.
1. The final response is returned to the user.
![Diagram showing Host with LLM and MCP Client connected to MCP Server, which includes Tools, Resources, and Prompts.](https://academy.hackthebox.com/storage/modules/315/diagram2.png)

Complex real-world LLM applications may allow multiple tools to be called in a single run. In that case, step 6 would be repeated until the LLM no longer wants to use any available tools.

---

## MCP Communication

After discussing a high-level overview of the MCP architecture, let us proceed to explore the MCP communication between the client and server. Messages transmitted in MCP follow the[JSON-RPC](https://www.jsonrpc.org/specification)format. The protocol defines three different types of messages:

- `Request`: A request message initiates an operation. It contains the members`id`, which is a unique request ID, and`method`, which specifies the type of operation to initiate. It may further contain the member`params`, which consists of the respective parameters.
- `Response`: A response message results from a previous request. It contains the same`id`member as the corresponding request. Furthermore, it contains either a`result`member or an`error`member, depending on the result of the respective operation.
- `Notification`: A notification message is a one-way message, i.e., there is no response. It does not contain an`id`member but only a`method`member and, if necessary, a`params`member.
MCP defines two different transport mechanisms to transmit the messages between client and server:

1. `stdio`: This transport mechanism uses the client and server processes' standard in and standard out provided by the operating system. It can only be used if the client and server run on the same local system.
1. `Streamable HTTP`: The MCP server starts an HTTP server. The client communicates with the server via HTTP GET and POST requests, while the server may use`Server-Sent Events (SSE)`to communicate with the client.[Server-Sent Events](https://html.spec.whatwg.org/multipage/server-sent-events.html)enable servers to push data to clients without previous client requests. This enables MCP servers to send request messages to the client without waiting for the client to make an HTTP request to the MCP server (`polling`).
---

## MCP Protocol Flow

To conclude the theoretical introduction to MCP, let us explore a typical protocol flow when an MCP client and an MCP server communicate. The MCP lifecycle consists of three phases:

- `Initialization`Phase
- `Operation`Phase
- `Shutdown`Phase
![Sequence diagram: Client and Server interaction. Initialization Phase with request, response, notification. Operation Phase with normal protocol operations. Shutdown, disconnect, and connection closed.](https://academy.hackthebox.com/storage/modules/315/diagram6.png)

##### Initialization

The first part, following an MCP client connecting to an MCP server, is the`initialization`. It consists of three messages. A client's first message after connecting is the`initialization request`. It contains at least the following information:

- The`method`member is set to`initialize`
- The`params`member contains the following information:- The latest MCP protocol version supported by the client in the`protocolVersion`key
- The capabilities supported by the client in the`capabilities`key
- General client information, such as client name and client version in the`clientInfo`key

The server responds to the initialization request with the`initialization response`containing at least the following information in the response's`result`member:

- The latest MCP protocol version supported by the server in the`protocolVersion`key
- The capabilities supported by the server in the`capabilities`key
- General server information, such as server name and server version, in the`serverInfo`key
To conclude the initialization phase, the client sends an`initialized notification`, a notification message. It contains no information except the`method`member, which is set to`notifications/initialized`.

Based on the information exchanged in the initialization request and response, the MCP client and server can agree on a specific MCP protocol version. If this is impossible due to incompatibilities, the client simply disconnects. Furthermore, the client and server exchanged information about supported capabilities, which can subsequently be interacted with in the`operation`phase.

##### Operation

The`operation`phase is the central part of MCP where the client and server exchange messages. This phase typically consists of requests and responses based on the information exchanged during the initialization process. For instance, depending on the server's capabilities, the client can interact with prompts, resources, and tools by sending a request message with the following`method`member:

- `prompts/list`: Retrieve a list of available prompts.
- `prompts/get`: Retrieve a specific prompt. The target prompt and potentially additional arguments are supplied in the`params`member.
- `resources/list`: Retrieve a list of available resources.
- `resources/templates/list`: Retrieve a list of available resource templates.
- `resources/read`: Retrieve resource contents. Both the URI and, in case of resource templates, additional parameters are supplied in the`params`member.
- `tools/list`: Retrieve a list of available tools.
- `tools/call`: Invoke a specific tool. The target tool and potentially additional arguments are supplied in the`params`member.
##### Shutdown

The shutdown may be initiated by either the client or the server. On the MCP level, no specific shutdown message is defined. In practice, the MCP session is terminated by terminating the underlying transport connection. More specifically, if the`stdio`transport mechanism is used, the input or output stream is closed. The HTTP connection is closed if the`Streamable HTTP`transport mechanism is used. After closing the transport mechanism, the MCP session is terminated.