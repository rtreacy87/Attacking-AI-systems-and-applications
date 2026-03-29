# Denial of ML Service

While ML deployments may be vulnerable to common Denial-of-Service (DoS) attack vectors, such as flooding the system with network traffic to overwhelm its resources, they can also be targeted by DoS attacks that directly exploit the deployment components. These attacks exploit the computational and algorithmic characteristics of ML models. For instance, attackers might flood an ML API with a high volume of queries, especially those designed to be computationally expensive, causing latency spikes, system crashes, or excessive resource consumption. More subtle forms of DoS attacks involve adversarial inputs crafted to trigger worst-case behaviors in the model, such as inputs that result in long inference paths or cause inefficient internal computations. These attacks are particularly concerning for systems that serve real-time or mission-critical functions, such as autonomous vehicles or fraud detection platforms. Generally, DoS attacks can lead to significant downtime, degraded user experience, or increased operational costs, particularly when ML models are run in cloud environments. Because these attacks can appear as normal usage, they are often difficult to detect and mitigate with traditional security measures.

---

## Sponge Examples

`Sponge Examples`, as introduced in[this](https://arxiv.org/pdf/2006.03463)paper, are specifically crafted adversarial inputs that maximize energy consumption and latency in the ML mode. As such, inference on these inputs forces the model to perform in the worst possible way in terms of power consumption and latency, making them a perfect fit for DoS attacks. In cases where the ML deployment runs on a battery-powered device (e.g., smartphones), high energy consumption may even drain the battery entirely, causing a complete outage in the ML system.

The basic idea behind sponge examples is to create ML inputs that result in high energy consumption or inference latency without increasing the input dimension. For obvious reasons, higher-dimensional inputs will require more computational effort to process. For instance, a longer input prompt to an LLM or a higher resolution input image to a visual model will require more computational work to process, thus directly resulting in higher energy consumption and latency. However, limiting the input dimension can prevent DoS attacks resulting from overly high-dimensional inputs. For instance, the input prompt to language models can be cut off after a maximum length, an input image scaled down to a lower resolution, or rejected entirely if it is too large. Therefore, sponge examples aim to increase computational work**without**increasing the input dimension.

#### Creating Sponge Examples

We can use a white-box or a black-box approach to create sponge examples. For the white-box approach, we need to be able to access the model's architectures and parameters. These requirements are unlikely to be met in real-world AI deployments. However, adversaries can use this approach by hosting their own classifier and developing sponge examples locally, which may transfer to other AI deployments using a similar architecture.

On the other hand, the black-box approach only requires adversaries to be able to query the model and subsequently measure either energy consumption or inference latency. While measuring the model's energy consumption is typically impossible, measuring inference latency is often realistic in classification services. Adversaries can simply query the model and measure the time it takes to compute the classification result to deduce the inference latency. Overall, the requirements for the black-box approach are commonly met in many real-world AI deployments.

In the paper,`genetic algorithms`are used to create sponge examples. They are an optimization technique inspired by the process of natural selection in biological evolution. Genetic algorithms evolve a population of candidate solutions over multiple generations, using mechanisms similar to biological evolution, such as`selection`,`crossover (recombination)`, and`mutation`. The following is a rough overview of how genetic algorithms work. However, we won't go into detail on them in this section:

1. `Initialization`: Start with a randomly generated population of potential examples
1. `Evaluation`: Each example is evaluated using a`fitness function`that measures its performance for the given problem. The evaluation involves querying the model with an example and measuring the fitness value, which can be either energy consumption or inference latency.
1. `Selection`: The fittest examples are more likely to be chosen to reproduce for the next generation. In our case, the fittest examples are those with`higher`energy consumption or inference latency, as our goal is to disrupt the service.
1. `Crossover`: Selected examples are combined to produce new offspring for the next generation. For instance, for text-based tasks, the left half of parent A is combined with the right half of parent B. For example, consider the samples`Hello World`and`HackTheBox Academy`. A crossover example of these two samples would be`Hello Academy`.
1. `Mutation`: Small, random changes are introduced to some examples to maintain genetic diversity and explore new areas of the solution space. For instance, for text-based tasks, words are mutated randomly.
1. `Replacement`: The new generation replaces the old one, and the process starts over with the`evaluation`phase. This process repeats until a stopping condition is met, such as a maximum number of generations or a target fitness level.
Each generation in a genetic algorithm consists of better sponge examples that are potentially more potent for DoS attacks. The paper's authors provide the source code for generating sponge examples[here](https://github.com/iliaishacked/sponge_examples), if you want to delve deeper into the generation process.

#### Denial of ML Service

After discussing the process of generating sponge examples, let us explore some basic principles that make sponge examples effective in DoS attacks.

Two principles for text-based sponge examples impact a model's processing time, and, by extension, energy consumption and inference latency. The first factor is the`output sequence length`. If a model generates more output tokens, more processing power is required to generate these tokens. As such, sponge examples aim to result in a response that is as long as possible. The second factor is the`number of input tokens`. Before processing a text response, each model represents the input as`tokens`. These tokens are learned and optimized in the training process to increase efficiency. Generally, the larger the number of tokens, the more data the model needs to process, which in turn requires more processing power. Since token representation is optimized, an input of the same length will not always result in the same number of tokens. Commonly used words generally result in fewer tokens, while rare or nonexistent words will result in more tokens. Thus, sponge examples generally aim to maximize the number of tokens, resulting in a more inefficient representation of the input data.

For instance, let us take a look at a few token representations of different input texts. Firstly, we need to install the required dependencies:

```
icantthinkofaname23@htb[/htb]`$pip3installtransformers`
```

Afterward, we can apply real-world model tokenizers to an input text using the following code. The code supports different models on[HuggingFace](https://huggingface.co/models).

Code:python```
`fromtransformersimportAutoTokenizerimportjson

model='openai-community/gpt2'while1:text=input("> ")tokens=AutoTokenizer.from_pretrained(model).tokenize(text)print(f"Number of Input Characters:{len(text)}")print(f"Number of Tokens:{len(tokens)}")print(json.dumps(tokens,indent=2))`
```

Let us run the code on different inputs and analyze the results:

```
icantthinkofaname23@htb[/htb]`$python3 sponge.py> This is an example text
Number of Input Characters: 23
Number of Tokens: 5
[
  "This",
  "\u0120is",
  "\u0120an",
  "\u0120example",
  "\u0120text"
]

> Athazagoraphobia
Number of Input Characters: 16
Number of Tokens: 7
[
  "A",
  "th",
  "az",
  "ag",
  "or",
  "aph",
  "obia"
]

> A/h/z/g/r/p/p/
Number of Input Characters: 14
Number of Tokens: 14
[
  "A",
  "/",
  "h",
  "/",
  "z",
  "/",
  "g",
  "/",
  "r",
  "/",
  "p",
  "/",
  "p",
  "/"
]`
```

A simple sentence such as`This is an example text`results in only five tokens, despite being 24 characters long. That is because the sentence consists of common words, which are all represented as a single token. The`\u0120`Unicode character results from the whitespace in front of the respective words in the input text. On the other hand, if we use a rare English word such as`Athazagoraphobia`, the 16-character input gets represented as seven tokens. Lastly, a text input consisting of character sequences that rarely ever exist in the English language, such as`A/h/z/g/r/p/p/`, results in 14 tokens for 14 input characters.

#### Effectiveness of Sponge Examples

An evaluation of the white-box approach shows that sponge examples can significantly increase energy consumption and inference latency. For instance, consider the following values in a translation task where the model runs on GPU hardware:

NaturalRandomSpongeEnergy Consumption (mJ)94922577340976Inference Latency (ms)0.10.240.37We can observe that random inputs lead to higher energy consumption and inference latency compared to natural inputs. This makes intuitive sense since models are optimized for natural inputs during training, as discussed earlier. Therefore, random inputs result in less optimized representation and thus more computational effort is required. Sponge examples are specifically designed to require a high computational effort, resulting in even higher energy consumption and inference latency compared to random inputs.

**Note:**These are just the results of one of many tasks performed. For an overview of all results, please check out the paper.

In a black-box setting, sponge examples achieve similar results. When exploring potential DoS attack vectors, it is crucial to consider ethical concerns to avoid causing actual disruptions to real-world services, which could result in financial harm to organizations or availability issues for users. As such, when evaluating the effectiveness of sponge examples, the authors limited the input length to 50 characters. With such a limited dimensionality, they were able to cause a significant increase in inference latency in a real-world ML service. More specifically, they increased the response time from an average of`1ms`to about`6s`in a Microsoft Azure translation service. These results demonstrate how a large-scale attack using sponge examples of higher input dimensions can significantly disrupt ML services in real-world deployments.

---

## Mitigations

Traditional DoS mitigations, such as rate limiting and anomaly detection, also apply to ML deployments. However, further mitigations are required to prevent ML-specific DoS attacks. These include query monitoring and robust model design to gracefully handle atypical input without a significant performance degradation. For instance, ML deployments can introduce a cutoff threshold for maximum energy consumption or inference time to protect from sponge examples. If the threshold is reached, the ML application returns an error message instead of a valid response to the input query. Such a threshold must be configured to prevent DoS attacks while not impeding benign user queries, as implementing overly strict countermeasures may result in a significantly reduced user experience.