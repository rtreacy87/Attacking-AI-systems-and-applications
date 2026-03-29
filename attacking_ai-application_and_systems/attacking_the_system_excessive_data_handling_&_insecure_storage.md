# Excessive Data Handling & Insecure Storage

Security vulnerabilities related to the insecure storage of data can result in unauthorized access. This can be particularly impactful in ML applications, as they typically process a large amount of potentially sensitive training and inference data. The impact is exacerbated if an application stores or processes data excessively, unnecessarily exposing the data to the risk of disclosure in the event of security vulnerabilities. If an AI application actively processes data that is not required for the primary purpose of the application, the`principle of data minimization`is violated. While collecting rich datasets can improve model performance, excessive or poorly managed data handling increases the attack surface and introduces significant privacy and security risks, which may result in legal repercussions, accompanied by potential reputational or financial damage.

---

## Insecure Data Storage

Let us explore a basic example of insecure data storage, putting processed and stored data at risk of leakage. If such a security vulnerability is combined with excessive data processing or storage, the impact is magnified. ML applications frequently store training data, intermediate results, logs, or user inputs for retraining or analytics purposes. If these data stores are not adequately secured, they can be prime targets for attackers. Insecure data storage can result from a lack of encryption or broken access control. Compromised data repositories may expose sensitive information, allowing for downstream attacks such as identity theft, profiling, or unauthorized model training. Such breaches are particularly critical in regulated industries, such as healthcare or finance, where data breaches can lead to severe legal consequences.

Insecure data storage vulnerabilities in ML applications extend beyond the ML model itself. The broader application ecosystem, including web frontends, APIs, and data processing pipelines, may all introduce risks. If adversaries gain access to these components, they could obtain unauthorized access to sensitive information.

For example, consider the chatbot on the`Pixel Forge`console shop website. It provides a service to recommend a gaming console based on the user's medical conditions:

**********![Beta - Pixel Forge Chatbot: User asks for help. Chatbot offers assistance in finding gaming consoles and suggests based on user needs. Message box with 'Hello World' and Send button.](https://academy.hackthebox.com/storage/modules/315/system/datastorage_1.png)Based on the medical condition provided by the user, the bot recommends a console sold by the shop:

**********![Beta - Pixel Forge Chatbot: User asks for console recommendation due to Snizzlewump Syndrome. Chatbot suggests NeuroDeck X1. Message box with 'Hello World' and Send button.](https://academy.hackthebox.com/storage/modules/315/system/datastorage_2.png)Furthermore, the chatbot asks the user for credit card information to place an order:

**********![Beta - Pixel Forge Chatbot: User asks for order information. Chatbot requests item ID and credit card number, offers suggestions based on medical conditions. Message box with 'Hello World' and Send button.](https://academy.hackthebox.com/storage/modules/315/system/datastorage_3.png)Medical and payment information are both highly sensitive data. Asking users to enter medical or credit card information into a chat most likely does not provide the care required to process such sensitive information. Chat messages may be logged and stored with requirements different from those for medical and payment information. While it is certainly a legitimate business case for a user to enter payment information on a webshop to order items, payment processes follow strict security requirements such as the`Payment Card Industry Data Security Standard (PCI DSS)`.

Excessive data handling can significantly increase the impact of vulnerabilities related to insecure data storage. As discussed previously, in a security assessment, we need to consider not only the ML model itself but also web application security. For instance, a fundamental part of web application security is`directory brute-forcing`, which attempts to identify HTTP endpoints offered by the web application. We can use a tool like`gobuster`to conduct directory brute-forcing:

```
icantthinkofaname23@htb[/htb]`$gobusterdir-u http://<SERVER_IP>:<PORT>/ -w /opt/SecLists/Discovery/Web-Content/raft-small-words.txt -x .db,.txt,.html

===============================================================
Gobuster v3.6
by OJ Reeves (@TheColonial) & Christian Mehlmauer (@firefart)
===============================================================
[+] Url:                     http://<SERVER_IP>:<PORT>/
[+] Method:                  GET
[+] Threads:                 10
[+] Wordlist:                /opt/SecLists/Discovery/Web-Content/raft-small-words.txt
[+] Negative Status codes:   404
[+] User Agent:              gobuster/3.6
[+] Extensions:              db,txt,html
[+] Timeout:                 10s
===============================================================
Starting gobuster in directory enumeration mode
===============================================================
/login                (Status: 200) [Size: 1183]
/register             (Status: 200) [Size: 1197]
/profile              (Status: 302) [Size: 199] [--> /login]
/logout               (Status: 302) [Size: 199] [--> /login]
/about                (Status: 200) [Size: 1223]
/storage.db           (Status: 200) [Size: 8876]
/store                (Status: 200) [Size: 4153]`
```

As we can see, the web application hosts a database file, which we can download using`wget`:

```
icantthinkofaname23@htb[/htb]`$wgethttp://<SERVER_IP>:<PORT>/storage.db

--2025-04-23 11:22:47--  http://<SERVER_IP>:<PORT>/storage.db
Connecting to <SERVER_IP>:<PORT>... connected.
HTTP request sent, awaiting response... 200 OK
Length: 8192 (8,0K) [application/octet-stream]
Saving to: ‘storage.db’

storage.db                                     100%[=====================================================================================================>]   8,00K  --.-KB/s    in 0s      

2025-04-23 11:22:47 (1,24 GB/s) - ‘storage.db’ saved [8876/8876]`
```

As we can see from the output of the`file`command, the file contains text:

```
icantthinkofaname23@htb[/htb]`$filestorage.dbstorage.db: ASCII text, with very long lines (533)`
```

Examining the file content, we can determine that it is a database dump containing all the data stored in the web application's database. In particular, the application logs all LLM queries in a table`llm_queries`, including the user's IP address, the query, and the generated response. As the queries potentially contain credit card or medical information, this is a critical data leak:

```
icantthinkofaname23@htb[/htb]`$catstorage.db[...]
CREATE TABLE `llm_queries` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `ip_address` text NOT NULL,
  `query` text NOT NULL,
  `response` text NOT NULL,
  PRIMARY KEY (`id`)
);

INSERT INTO `llm_queries` VALUES
(5,1,'172.17.0.1','Awesome. In that case I want to order the PhantomArc SP. My credit card number is 4777752566795752 ','Unable to place order. Please try ordering your console manually.');
[...]`
```

While this example is certainly overly simplistic and real-world instances of insecure data storage are rarely this obvious, it demonstrates how misconfigurations within the web application can put ML-related data at risk. The impact of insecure data storage vulnerabilities is significantly higher if the application implements excessive data processing, potentially putting sensitive user information at risk even though it is not required to operate the ML application. In a more realistic scenario, common web vulnerabilities such as SQL injection may put ML-related data at risk, resulting in the same or even more severe consequences as our simplistic example.

---

## Mitigations

Organizations must implement strong data governance to mitigate excessive data handling. Most importantly, this includes strictly adhering to the`principle of data minimization`, i.e., collecting only the data vital for the ML task, and avoiding excessive data collection. Privacy policies and user consent mechanisms must be tightly aligned with actual data practices to prevent legal violations such as breaches of GDPR, HIPAA, or similar data protection regulations. If applicable, ML applications should utilize techniques such as`data anonymization`or`differential privacy`, thereby minimizing the risk that mishandled datasets could expose sensitive information even in the event of a breach. To reduce the risk of data breaches, we must follow security best practices regarding secure data storage. These include strong`access control mechanisms`,`encryption`, and`data retention policies`to ensure that data is automatically deleted when it is no longer needed.

Furthermore, to reduce the risk of data loss, an ML application could avoid plaintext data entirely by utilizing`Homomorphic Encryption (HE)`. HE allows computations to be performed directly on encrypted data, producing encrypted results that, when decrypted, match the outcome of operations performed on the raw data. In ML applications, this could enable a model to run on encrypted training and inference data, ensuring that even if the data storage is compromised, the data remains protected and usable for computation without sacrificing confidentiality. However, HE adds a significant performance overhead to all computations, making it infeasible for many real-world ML applications.