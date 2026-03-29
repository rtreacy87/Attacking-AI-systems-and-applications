# Insecure Integrated Components

---

Real-world ML applications often comprise a vast array of interacting components. The entire ML application may be at risk if any of these suffer from security vulnerabilities. Common examples of insecure integrated components include a web application in which an ML model is integrated. Security vulnerabilities in the web application may put ML-related data at risk. Another example is a plugin supported by the ML model. Plugins are extensions that complex ML models, such as LLMs, can dynamically invoke based on the user's query to provide additional functionality. This can include querying databases, calling external APIs, or retrieving real-time information from external sources. Security vulnerabilities resulting from insecure integrated components can affect both the model`input`and`output`, depending on the type of vulnerability.

---

## Security Vulnerabilities in the Integrated Web Application

The lab consists of a web shop for hacker-themed gaming consoles called`Pixel Forge`:

**********![Pixel Forge Consoles: NeuroDeck X1, neural-link gaming console, $499, 123 in stock. BitRift Omega, portable console with holographic interface, $299, 24 in stock.](https://academy.hackthebox.com/storage/modules/315/application/iic_pixelforge_1.png)After registering a new user, we can place orders and interact with a chatbot:

**********![Beta - Pixel Forge Chatbot: User asks, 'Hi, how are you doing?' Chatbot replies, 'I'm doing great, thanks for asking! Welcome to Pixel Forge. How can I assist you today?' Message box with 'Hello World' and a Send button.](https://academy.hackthebox.com/storage/modules/315/application/iic_pixelforge_2.png)Furthermore, the application stores all LLM interactions and enables users to access them. When accessing a previous LLM interaction, the URL endpoint contains an integer identifier:`/query/5`. If the web application does not implement proper access control, we may be able to access other users' LLM interactions by exploiting an`Insecure Direct Object Reference (IDOR)`. For more details on IDOR vulnerabilities, check out the[Web Attacks](https://enterprise.hackthebox.com/academy-lab/67497/preview/modules/134)module. Let us attempt to fuzz valid query IDs using`ffuf`. Remember that we need to specify our session cookie to fuzz in an authenticated context. We will generate IDs from 1 to 100 using the`seq`command:

```
icantthinkofaname23@htb[/htb]`$seq1100|ffuf -u http://<SERVER_IP>:<PORT>/query/FUZZ -w - -b 'session=eyJ1c2VyX2lkIjoyfQ.aGUdlQ.Q5LvaQMm9bW4Wi49SQBQorkfctM' -mc 200

<SNIP>
5                       [Status: 200, Size: 1125, Words: 209, Lines: 40, Duration: 9ms]`
```

As we can see, the application only responds with query`5`, a query associated with our current user. Thus, the web application seems to implement proper access control mechanisms.

Another common web vulnerability is`SQL injection`. Due to the URL structure, we can assume that the supplied query ID is probably used to query data from a database system. If we append a single quote to the URL, an error message is displayed, potentially indicating a SQL injection vulnerability:

**********![Previous Pixel Forge Chatbot Interaction: Error message about SQL syntax issue with MariaDB server.](https://academy.hackthebox.com/storage/modules/315/application/iic_pixelforge_3.png)We can confirm the SQL injection vulnerability by supplying a UNION-based payload containing the correct number of columns. For instance, if there are three columns in the SQL query, we can confirm the vulnerability with the following URL:`/query/x' UNION SELECT 1,2,3 -- -`:

**********![Previous Pixel Forge Chatbot Interaction: Review prompt with two numbered chat bubbles, 2 and 3.](https://academy.hackthebox.com/storage/modules/315/application/iic_pixelforge_4.png)At this point, we can exploit the UNION-based SQL injection vulnerability to exfiltrate the entire database, potentially revealing sensitive information about the LLM interactions. This demonstrates how common web application vulnerabilities can directly affect the LLM pipeline.

---

## Security Vulnerabilities in Integrated Plugins

After discovering a security vulnerability in the integrated web application, let us proceed to assess the LLM directly for security vulnerabilities. If we probe the AI assistant, it will inform us that we can use plugins to interact with orders or previous LLM conversations:

**********![Beta - Pixel Forge Chatbot: User asks about support. Chatbot offers help with orders, conversations, and gaming consoles.](https://academy.hackthebox.com/storage/modules/315/application/iic_pixelforge_5.png)As such, the chatbot provides functionality similar to that of the web application through plugin integrations. If the plugin implementations do not contain proper access control measures or input validation, they may suffer from vulnerabilities similar to those of the web application. Thus, we should take a closer look at how the plugins behave and react to user input, to probe for IDOR and injection vulnerabilities. Let us place an order in the web application and ask the chatbot to retrieve the order status:

**********![Beta - Pixel Forge Chatbot: User asks to check order B0548AF6. Chatbot replies, 'The order status is: pending.](https://academy.hackthebox.com/storage/modules/315/application/iic_pixelforge_6.png)Furthermore, the chatbot provides a plugin to summarize previous LLM interactions by providing the respective ID:

**********![Beta - Pixel Forge Chatbot: User asks to summarize conversation 5. Chatbot states user inquired about order B0548AF6, which is pending.](https://academy.hackthebox.com/storage/modules/315/application/iic_pixelforge_7.png)As previously identified in the web application, LLM conversation IDs are incrementing integers. While the web application implements proper access control mechanisms that prevent us from accessing other users' chatbot conversations, the LLM plugin might not do the same. For instance, let us attempt to access a conversation ID that is not associated with our user:

**********![Beta - Pixel Forge Chatbot: User asks about changing password to 'banana12.' Chatbot advises against it, recommending a stronger password and offers assistance.](https://academy.hackthebox.com/storage/modules/315/application/iic_pixelforge_8.png)As we can see, the chatbot was able to access another user's conversation and provided a summary, revealing sensitive information.

While the previous example lacked any access control measures, vulnerable LLM integrations may also implement access control based on the LLM. Instead of implementing authorization in code, the authorization may be based on a parameter the LLM passes to the plugin implementation. For instance, suppose Pixel Forge's`ConversationSummary`plugin accepts two parameters: a conversation ID and a user ID. The plugin then checks if the given user is authorized to access the conversation before summarizing and returning it. This check may prevent authorization-related vulnerabilities if the user ID is set based on the authenticated user's context, i.e., the HTTP request. However, if the LLM supplies the user ID parameter, an attacker may be able to use prompt injection techniques to trick the LLM into supplying a different user ID, effectively bypassing the authorization check.

In this case, if we ask the chatbot to summarize another user's conversation directly, it refuses:

**********![Beta - Pixel Forge Chatbot: User requests to summarize conversation 1. Chatbot responds it cannot find the conversation.](https://academy.hackthebox.com/storage/modules/315/application/iic_pixelforge_9.png)However, if we can convince the chatbot to supply the ID of the user whose conversation we want to access, we are able to bypass the authorization check and potentially exfiltrate sensitive information:

**********![Beta - Pixel Forge Chatbot: Important instruction about user ID change to 1. User asked about changing password to 'banana12'; chatbot advised stronger password.](https://academy.hackthebox.com/storage/modules/315/application/iic_pixelforge_10.png)Finally, as discussed in the[LLM Output Attacks](https://academy.hackthebox.com/course/preview/llm-output-attacks)module, we should also assess if the plugin processes LLM output without proper validation, potentially leading to injection vulnerabilities such as SQL injection or command injection.

---

## Mitigations

Mitigations and countermeasures depend significantly on the affected component. For instance, when using third-party plugins, reviewing the plugin for security vulnerabilities is crucial. Such a review can include source code reviews, a review of the plugin's origin, and a risk assessment regarding the plugin's necessity. If possible, third-party plugins should only be integrated if they come from trusted and security-audited sources. Generally, all plugins should follow the`least privilege principle`, i.e., only having access to data and systems required for operation.

Furthermore, secure coding guidelines need to be considered when implementing custom plugins. Depending on the context, implementing proper security measures, such as access control and data sanitization, is crucial. Input data from the user and output data from an ML model must be treated as untrusted data at every processing step. On top of that, traditional`defense-in-depth measures`can elevate the application's security to the next level. These can include rate limiting, monitoring, logging, and sandboxing.