# singularity-prelude
Decoder-only generative pretrained transformer, and byte pair encoding tokeniser.


### Example outputs, trained on <a href="https://huggingface.co/datasets/HuggingFaceFW/fineweb/tree/main/sample/10BT">FineWeb 10BT sample</a>

  #### Hyperparameters:
  Vocab size: `8192`  
  Context window: `256`  
  Embedding dimension: `1024`  
  Layers num: `16`  
  Heads num: `16`  
  Approx parameter count: `210m - 220m`  

####  Why the short context window?  
  My primary goal was to generate some tangible short texts, instead of being able to continue to make sense for a long output.

  
  #### Training loss: `3.2752` Validation loss: `3.4626`
  #### Prompt: `Once upon a time, in a small village surrounded by mountains, there lived`
  > Once upon a time, in a small village surrounded by mountains, there lived a beautiful and enchanting garden. In the town of Chiang Mai, it was the home of Sung, the crowned Kongo of Asian culture, to see the seaside area of the nation. The town was also home to an active community of locals, with a huge collection of monasteries, lakes and giant bays which became a main attraction at the turnaround.
  The village has been attracting tourists ...
  #### Prompt: `The meaning of life is`
  > The meaning of life is a simple question. I am a human being. In many ways life is a complex question, and it is only when that is that that is an answer.
  A life is not an abstract question, but a basic question: When does life begin? How does life start?
  This will be the first part of the book. The first part of the book is about how life became a fun question. A personal statement such as this is the first part of the book. A personal ...
<!--
  #### Prompt: `Yesterday I went to the supermarket and`
  > Yesterday I went to the supermarket and got the first two sides. I was very disappointed with the price of the pants. The pants I got are a really nice and expensive shirt. They are not cheap to buy but there is a small difference in price. I did purchase the pants at the supermarket so I can only buy them for the $69.00 price to find a good deal.
  I love the pants and it makes me feel pretty good and I am happy as a customer. ...

  #### Prompt: `Alice: Hey, are you coming to the party tonight?\nBob`
  > Alice: Hey, are you coming to the party tonight?  
  Bob: I do not care about you getting an opportunity to express my love for you, and I don't want you to get a chance to talk, so I will just take a moment to respond to your heartfelt voice and give you a few minutes of comfort in the room.  
  Glenn: Well, I'm very excited about you. I will get a chance to show you some very good things about this party.  
  Bob: Okay, I'm pretty excited. What I like to say is ...
-->
  #### Prompt: `It was a cold and rainy evening when Sarah heard a strange noise coming from the kitchen`
  > It was a cold and rainy evening when Sarah heard a strange noise coming from the kitchen.
  A short while later, the kitchen was filled with the most amazing dishes and a beautiful open floor plan. I wish Sarah would have stayed here with us all if she had to go to see the kitchen again during the winter months.
  The room was packed, and Sarah was able to put together some delicious supplies for the breakfast on the table as well.
  I also wanted to give Sarah some space at the kitchen where her husband is able to sit down and take ...

<!--
### Transformer information
- GPT architecture
- Multi-headed casual attention
-->
### Example `transformer.py` usage (training):

Modify lines `129 - 152` to set hyperparameters:
```python
torch.manual_seed(67)
# vocabSize = len(tokens)
vocabSize = 8192
blockSize = 256 # context size
embedSize = 1024
blockNum = 16
headNum = 16

feedForwardSize = 4
headSize = embedSize//headNum # must be divisible
dropout = 0.1

batchSize = 16
evalIters = 100
evalInterval = 10000
saveInterval = 2000
printInterval = 2000
trainIters = 1000000
trainEpochs = 3

learningRate = 1e-4
betas = (0.9, 0.95)
epsilon = 1e-8
weight_decay = 0.1

```
Requires pre-tokenised training set.
```python
# line 77 and 102, replace "train_data/{}.bin" with actual location of tokenised training set.
currentTrainData = torch.from_numpy(np.fromfile(f"train_data/{currentTrainFile}.bin", dtype=np.uint16)).long()
```
Requires validation set as parquet files.
```python
# line 65, replace "data/paraqeet/valorant" with actual location of parquet validation set.
"data/paraqeet/valorant",
```
Requires trained tokeniser (V1 - V3).
```python
# line 10 - 14
import bigT2 # replace with version used

t = bigT2.Tokenizer() # replace with version used

t.load("data/tiktoks/checkpoint7931") # replace with location of saved tokeniser

```

Run `transformer.py`.   
Outputs trained model to `model.pth`.  

### Example `transformer.py` usage (generation):

```python
maxTokens = 100
temperature = 0.8
topK = 50
topP = 0.9
repetitionPenalty = 1.15

prompt = """Why did the chicken cross the road"""
g = model.generate(encode(prompt).to(device), maxTokens, temperature, topK, topP, repetitionPenalty).cpu().tolist()
text = t.fromBytes(t.decode(g))
print(text)

```


### Tokeniser Information

#### V1 `bigT.py`
Uses doubly linked lists for O(1) replacements of token pairs, pointers to keep track of every occurrence of every pair, min heap with lazy invalidation for getting the most common pair.

#### V2 `bigT2.py`
Uses separate linked list module, and other minor changes.  

#### V3 `bigT2_5.py`
Complete rewrite. Uses flat array linked lists instead for improved performance, same core functionality.  
Requires the usage of `converter.py` when using saved tokenisers trained using `bigT` and `bigT2`.

Example Usage:
```python
# training
import bigT, bigT2, bigT2_5
t = bigT2_5.Tokenizer() # swap out for bigT2, bigT (identical usage)
with open("corpus.txt", encoding="utf-8") as f:
	t.corpus = f.read()
t.build(2048)
t.save("token2048")

# usage
t.load("token2048")
print(t.encode("Hello world!"))
print(t.fromBytes(t.decode(t.encode("Hello world!"))))
```

#### V4 `cpp/encoderTest.cpp`
Rewrite of `bigT2_5` into C++ for significant performance improvement. Includes only `encode` and `load` functionality, with no `build` or `decode`.  
Requires the usage of `converter.py` when using saved tokenisers trained using `bigT` and `bigT2`.  
Used for pre-tokenising entire files.  
Example Usage:
```C++
Tokenizer t = Tokenizer();
t.load("converted2048.json");
string text = t.loadString("sample.txt");
t.saveBin(t.encode(text), "sample.bin");
```
#### converter `data/tiktoks/converter.py`
Used to convert the saved trained tokenisers created by `V1` and `V2` to the format used by `V3` and `V4`.  
Usage:
```python
# ...
name = "token2048" # edit line 5
newName = "converted2048" # edit line 6
# run converter.py
# outputs converted2048.json, the format used by V3 and V4.
```



