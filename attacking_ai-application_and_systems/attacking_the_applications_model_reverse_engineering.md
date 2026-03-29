# Model Reverse Engineering

Model reverse engineering is an attack on an AI application in which an adversary attempts to reconstruct or approximate the deployed model. By systematically sending inputs to the model through an exposed API and observing the outputs, the adversary collects enough input-output data points to train a`surrogate model`that mimics the original model's behavior. This process can be executed as a black-box attack, i.e., it does not require access to the internal model architecture or training data, making it particularly dangerous for publicly accessible AI applications.

This type of attack poses multiple risks. For commercial ML providers, model reverse engineering can result in intellectual property theft, potentially undermining years of research and development investment. For security-sensitive applications, such as spam detection, facial recognition, or fraud detection systems, an extracted model can be used to probe for vulnerabilities or generate adversarial examples that bypass defenses. Moreover, if the original model is trained on sensitive data, a sufficiently accurate clone could be used for`model inversion attacks`, where the adversary attempts to reconstruct sensitive information about the training data.

---

## Reverse Engineering an ML Model

Let us explore a basic example of a model reverse engineering attack. Although the following implementation is not feasible for larger and more complex models, the underlying concept remains the same.

#### The Classifier

In this section, we will explore a classifier that classifies two species of penguins,`Adélie`and`Gentoo`, based on their flipper length in Millimeters and body mass in Grams. This classifier is based on a well-known[public dataset](https://allisonhorst.github.io/palmerpenguins/). Furthermore, the classification task does not require a complex classifier. As such, we could easily train a similar classifier ourselves based on the public dataset. However, for this section, we will assume that the training data is not publicly available, such that we need to execute a model reverse engineering attack to obtain our own classifier.

The classification service is provided in a web API, enabling us to interact with the classifier by providing the two variables, flipper length and body mass, in the GET parameters`flipper_length`and`body_mass`, respectively:

```
icantthinkofaname23@htb[/htb]`$curl'http://172.17.0.2/?flipper_length=150&body_mass=5000'{"result": "Adelie"}`
```

#### Sampling Datapoints

To reverse engineer the model, we first need to sample data points on which to train the surrogate model. For this, we need to generate pairs of flipper length and body mass. We can then run the model on these input pairs to obtain the corresponding output. In the final step, we can use these input-output data points to train our classifier.

In our code, we will use random generation to obtain a large number of input data points. To improve the data quality, we should consider prior information in our random sampling process. For instance, we could research a realistic range of penguin flipper lengths and body masses to obtain lower and upper boundaries. This ensures that we only obtain high-quality data points in our random sampling, thereby improving training performance by reducing the number of data points required for the training process. Depending on the type of classification problem, we may be unable to define meaningful boundaries for our input data points. In these cases, we need a significantly larger number of data points to successfully reverse-engineer the model, due to the lower quality of the data.

In our example, we will restrict the flipper length to`150-250mm`and the body mass to`2500-6500g`. Let us start by defining the following parameters for our code:

Code:python```
`N_SAMPLES=100MIN_FLIPPER_LENGTH=150MAX_FLIPPER_LENGTH=250MIN_BODY_MASS=2500MAX_BODY_MASS=6500CLASSIFIER_URL="http://172.17.0.2:80/"`
```

Now, we can uniformly sample random data points within these boundaries:

Code:python```
`importrandomimportpandasaspd

samples={"Flipper Length (mm)":[],"Body Mass (g)":[]}foriinrange(N_SAMPLES):samples["Flipper Length (mm)"].append(random.uniform(MIN_FLIPPER_LENGTH,MAX_FLIPPER_LENGTH))samples["Body Mass (g)"].append(random.uniform(MIN_BODY_MASS,MAX_BODY_MASS))samples_df=pd.DataFrame(samples)print(samples_df.head())`
```

Executing the code, we can observe the first couple of data points we generated:

```
icantthinkofaname23@htb[/htb]`$python3 model_stealer.pyFlipper Length (mm)  Body Mass (g)
0           249.330146    3107.061717
1           249.818948    6443.306983
2           210.936472    4121.976351
3           208.697770    5145.900243
4           158.819736    3882.060817`
```

For the training process, we require the respective predicted classes for all input data points. To obtain these, we can feed the input data to the original model via the web API and observe the predicted classes. In our code, we can achieve this by iterating over the generated data points, calling the web API, and storing the predicted classes in a new DataFrame:

Code:python```
`importrequestsimportjson

predictions={"species":[]}foriinrange(N_SAMPLES):sample={"flipper_length":samples["Flipper Length (mm)"][i],"body_mass":samples["Body Mass (g)"][i]}prediction=json.loads(requests.get(CLASSIFIER_URL,params=sample).text).get("result")predictions["species"].append(prediction)predictions_df=pd.DataFrame(predictions)print(predictions_df.head())`
```

As a result, we now know the predicted classes for all randomly generated data points:

```
icantthinkofaname23@htb[/htb]`$python3 model_stealer.pyspecies
0  Gentoo
1  Gentoo
2  Gentoo
3  Gentoo
4  Adelie`
```

#### Replicating the Model

The final step in reverse engineering the original model is to train the surrogate model on the data obtained in the previous step. One of the main factors deciding the model's quality is the model architecture we choose. While different model architectures are known to perform well for specific tasks, such as CNN architectures for image classification or LLM architectures for text generation, we often do not know the exact architecture used by the original model. As such, it is often impossible to re-create the original model exactly. However, choosing an identical architecture is often not required, as long as we select one that suits the specific task we want the model to accomplish.

In our penguin example, we will train a`Logistic Regression`classifier since we are interested in a binary classification setting. For more details on this type of classifier, refer to the[Fundamentals of AI](https://enterprise.hackthebox.com/academy-lab/67497/preview/modules/290)module.

We can train a classifier on our training data using the following code:

Code:python```
`fromsklearn.pipelineimportmake_pipelinefromsklearn.preprocessingimportStandardScalerfromsklearn.linear_modelimportLogisticRegressionimportjoblib

surrogate_model=make_pipeline(StandardScaler(),LogisticRegression())surrogate_model.fit(samples_df,predictions_df)# save classifier to a filejoblib.dump(surrogate_model,'surrogate.joblib')`
```

#### Evaluation

To submit the surrogate model to the lab, we can upload it to the lab's`/model`endpoint:

Code:python```
`withopen('surrogate.joblib','rb')asf:file=f.read()r=requests.post(CLASSIFIER_URL+'/model',files={'file':('surrogate.joblib',file)})print(json.loads(r.text))`
```

Executing the code, the lab returns the accuracy we achieved on a test set:

```
icantthinkofaname23@htb[/htb]`$python3 model_stealer.py{'accuracy': 0.9854014598540146}`
```

As we can see, the surrogate model achieved an accuracy of more than`98%`, which is an excellent result considering we only sampled 100 data points. Remember that we were able to train this classifier without access to any real-world training data, as we randomly generated data points and used the web API to obtain the target classes.

#### Comparing the Models

As a final step, let us take a look behind the scenes and compare the surrogate model to the original one. The decision boundary of the original model looks like this:

![Scatter plot with decision boundary separating Gentoo and Adelie penguins by flipper length and body mass.](https://academy.hackthebox.com/storage/modules/315/application/og_model.png)

The decision boundary of the surrogate model is only marginally different from that of the original model. By training the classifier on more data points, we can further reduce the difference.

![Scatter plot with decision boundary: Gentoo and Adelie penguins, flipper length vs. body mass.](https://academy.hackthebox.com/storage/modules/315/application/stolen_model.png)

---

## Mitigations

Since attackers conducting a model reverse engineering attack query the model like any benign user, mitigating these attacks is challenging. Restricting access to the model completely by blocking access to the available service, e.g., a web API, would also severely affect benign users. However, many real-world models worth protecting from model reverse engineering are significantly more complex than the one we discussed. Therefore, attackers require a lot of data points to reverse engineer the model, many magnitudes more than what we implemented in this section. Since the adversary must query the original model for every data point to obtain the target value, they produce significant network traffic. Model reverse engineering attacks can thus be mitigated or slowed down by limiting access to the model. Typical examples for this include`rate limiters`in web APIs that only allow a fixed number of queries in a specific time frame. Depending on the rate limiter's configuration, it can effectively mitigate model reverse engineering. However, it is crucial not to be overly strict with rate limiter configurations so as not to impede benign user queries.