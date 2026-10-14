import torch
import torch.nn as nn
import torch.nn.functional as F

import bigT

t = bigT.Tokenizer()
t.load()

# tokens = ['\n', ' ', '!', '$', '&', "'", ',', '-', '.', '3', ':', ';', '?', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
# tokenDecode = {n:i for n, i in enumerate(tokens)}
# tokenEncode = {i:n for n, i in enumerate(tokens)}





def encode(text):
	return torch.tensor(t.encode(text))
	# return torch.tensor([tokenEncode[c] for c in text])

def decode(tokens):
	return t.decode(tokens)
	# return "".join([tokenDecode[t.item()] for t in tokens])


with open("cleaned_text.txt", encoding="utf-8") as f:
	trainData = encode(f.read())
	dataLength = len(trainData)
	splitPos = round(dataLength * 0.9)

def getBatch(split = "train"):
	if split == "train":
		pos = torch.randint(splitPos, dataLength - blockSize, (batchSize, ))
	else:
		pos = torch.randint(0, splitPos - blockSize, (batchSize, ))
	# print(encode(trainData[pos[0]:pos[0]+blockSize]))
	# print(encode(trainData[pos[1]:pos[1]+blockSize]))
	# print()
	x = torch.stack([trainData[p:p+blockSize] for p in pos])
	y = torch.stack([trainData[p+1:p+blockSize+1] for p in pos])
	return x, y



# hyperparameters

torch.manual_seed(67)
# vocabSize = len(tokens)
vocabSize = 1024 + 256
blockSize = 32 # context size
embedSize = 256 # embedding dimension
batchSize = 32
blockNum = 8
feedForwardSize = 4 

headNum = 8
headSize = embedSize//headNum # must be divisible
dropout = 0.2

evalIters = 50
evalInterval = 1000
saveInterval = 1000
trainIters = 0
learningRate = 1e-4


class Head(nn.Module):
	def __init__(self):
		super().__init__()
		self.key = nn.Linear(embedSize, headSize, bias=False)
		self.query = nn.Linear(embedSize, headSize, bias=False)
		self.value = nn.Linear(embedSize, headSize, bias=False)
		self.register_buffer("triu", torch.triu(torch.ones(blockSize, blockSize, dtype = torch.bool), diagonal = 1))
		self.normFactor = headSize ** -0.5
		self.dropout = nn.Dropout(dropout)

	def forward(self, x):
		B, T, C = x.shape
		k = self.key(x)
		q = self.query(x)
		v = self.value(x)
		out = k @ q.transpose(-1, -2) # swapping time and channels so dotting
		out = out * self.normFactor # not in place, because apparently it might cause some problems with autograd? can try remove later
		out = out.masked_fill(self.triu[:T, :T], float("-inf")) 
		out = F.softmax(out, -1)
		out = self.dropout(out)

		out = out @ v 
		return out





class Block(nn.Module):
	def __init__(self):
		super().__init__()
		self.heads = nn.ModuleList([Head() for i in range(headNum)])
		self.layerNorm = nn.LayerNorm(embedSize)
		# self.layerNorm2 = nn.LayerNorm(embedSize)
		self.dropout = nn.Dropout(dropout)
		self.proj = nn.Linear(embedSize, embedSize)

		self.feedForward = nn.Sequential( # try different activation functions or ff structure later maybe
			nn.LayerNorm(embedSize),
			nn.Linear(embedSize, embedSize * feedForwardSize),
			nn.ReLU() ,
			nn.Linear(embedSize * feedForwardSize, embedSize),
			nn.Dropout(dropout)
		)

	def forward(self, x):
		h = self.layerNorm(x)
		h = torch.cat([i(h) for i in self.heads], dim = -1)
		h = self.dropout(h)
		h = self.proj(h)
		x = x + h
		x = x + self.feedForward(x)
		return x







class Model(nn.Module):
	def __init__(self):
		super().__init__()
		self.posEmbed = nn.Embedding(blockSize, embedSize)
		self.tokEmbed = nn.Embedding(vocabSize, embedSize)

		self.blocks = nn.Sequential(*[Block() for i in range(blockNum)], nn.LayerNorm(embedSize))
		self.lmHead = nn.Linear(embedSize, vocabSize)

	def forward(self, x, y = None): # assume maxed out block size

		xp = self.posEmbed(torch.arange(0, min(len(x[0]), blockSize)))
		tp = self.tokEmbed(x)
		x = xp + tp

		x = self.blocks(x)
		logits = self.lmHead(x)
		if y == None:
			loss = None
		else:
			B, T, C = logits.shape
			logits = logits.view(B*T, C)
			targets = y.view(B*T)
			loss = F.cross_entropy(logits, targets)
		return logits, loss


	@torch.no_grad()
	def estimateLoss(self):
		self.eval()
		out = {}
		for split in ["train", "val"]:
			losses = torch.zeros(evalIters)
			for i in range(evalIters):
				x, y = getBatch(split)
				logits, loss = self(x, y)
				losses[i] = loss.item()
			out[split] = losses.mean()
		self.train()
		return out


	@torch.no_grad()
	def generate(self, tokens, maxTokens):
		# tokens = start[:-blockSize].unsqueeze(0)
		tokens = tokens.unsqueeze(0)
		self.eval()
		for i in range(maxTokens):
			# tokens = tokens[:,:-blockSize]
			logits = self(tokens[:,-blockSize:])[0] # [0] to get logits and ignore loss return
			logits = F.softmax(logits[:,-1,:], dim = -1)
			# print(logits)
			nextToken = torch.multinomial(logits, num_samples=1)
			tokens = torch.cat((tokens, nextToken), dim = 1)
		self.train()
		return tokens[0]




def save(model, optimizer, step):
	torch.save({
		"model": model.state_dict(),
		"optimizer": optimizer.state_dict(),
		"step": step
	}, "model.pth")

def load():
	return torch.load("model.pth", weights_only = False)








model = Model()
optimizer = torch.optim.AdamW(model.parameters(), lr = learningRate)
step = 0
# print(decode(model.generate(encode("\n"), 100)))
try:
	loaded = load()
	model.load_state_dict(loaded["model"])
	optimizer.load_state_dict(loaded["optimizer"])
	step = loaded["step"]
except:
	print("failed to load frfr")

while step < trainIters:
	x, y = getBatch()
	logits, loss = model(x, y)
	optimizer.zero_grad(set_to_none=True)
	loss.backward()
	optimizer.step()

	if step % evalInterval == 0:
		print(step, model.estimateLoss())
	if step % saveInterval == 0:
		save(model, optimizer, step)
		print("saved at step", step)
	step += 1

print("done!")
save(model, optimizer, step)
print(model.estimateLoss())

print(decode(model.generate(encode("To be or not to be, "), 1000)))



# print(getBatch())