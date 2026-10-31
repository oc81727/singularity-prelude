import torch
import torch.nn as nn
import torch.nn.functional as F
from datasets import load_dataset
import time

import bigT2

t = bigT2.Tokenizer()
# t.load("data/tiktoks/newtokens32768")
t.load("data/tiktoks/checkpoint7931") # 8192 tokens
# t.load("tok2048")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"using device: {device}")

# tokens = ['\n', ' ', '!', '$', '&', "'", ',', '-', '.', '3', ':', ';', '?', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
# tokenDecode = {n:i for n, i in enumerate(tokens)}
# tokenEncode = {i:n for n, i in enumerate(tokens)}





def encode(text):
	return torch.tensor(t.encode(text))
	# return torch.tensor([tokenEncode[c] for c in text])

def decode(tokens):
	return t.decode(tokens)
	# return "".join([tokenDecode[t.item()] for t in tokens])


# with open("cleaned_text.txt", encoding="utf-8") as f:
# 	trainData = encode(f.read())
# 	dataLength = len(trainData)
# 	splitPos = round(dataLength * 0.9)




trainDataset = load_dataset(
	"data/paraqeet/iliketrains",
	data_files="*.parquet",
	split="train",
	streaming=True,
)
trainPointer = 0
def iterateDataset(dataset, skip = 0):
	dataset.skip(skip)
	while True:
		print("start of dataset!")
		for item in dataset:
			yield item

trainIter = iterateDataset(trainDataset, trainPointer)
trainData = t.encode(next(trainIter).get("text"))
trainData.append(260)
# end of document token


valDataset = load_dataset(
	"data/paraqeet/valorant",
	data_files="*.parquet",
	split="train",
	streaming=True,
)
valPointer = 0
valIter = iterateDataset(valDataset, valPointer)

valData = t.encode(next(valIter).get("text"))
valData.append(260)





def getBatch(split = "train"):
	global trainData, valData, trainPointer, valPointer
	batch = []
	# print(trainData)
	if split == "train":
		for i in range(batchSize):
			currentEntry = []
			while len(currentEntry) < blockSize + 1:
				ex = blockSize + 1 - len(currentEntry)
				currentEntry.extend(trainData[:ex])
				trainData = trainData[ex:]
				if len(trainData) == 0:
					# s = time.time()
					trainPointer += 1
					trainData = t.encode(next(trainIter).get("text"))
					trainData.append(260)
					# e = time.time()
					# print(f"tokenizing took {e - s} seconds")
			batch.append(currentEntry)
	else:
		for i in range(batchSize):
			currentEntry = []
			while len(currentEntry) < blockSize + 1:
				ex = blockSize + 1 - len(currentEntry)
				currentEntry.extend(valData[:ex])
				valData = valData[ex:]
				if len(valData) == 0:
					# s = time.time()
					valPointer += 1
					valData = t.encode(next(valIter).get("text"))
					valData.append(260)
					# e = time.time()
					# print(f"tokenizing took {e - s} seconds")
			batch.append(currentEntry)

	# x = torch.stack([torch.tensor(entry[:-1]) for entry in batch])
	x = torch.tensor([entry[:-1] for entry in batch], device = device)
	# y = torch.stack([torch.tensor(entry[1:]) for entry in batch])
	y = torch.tensor([entry[1:] for entry in batch], device = device)
	return x, y


# hyperparameters

torch.manual_seed(67)
# vocabSize = len(tokens)
vocabSize = 8192
blockSize = 512 # context size
embedSize = 256 # embedding dimension
batchSize = 64
blockNum = 6
feedForwardSize = 4 

headNum = 4
headSize = embedSize//headNum # must be divisible
dropout = 0.1

evalIters = 50
evalInterval = 1000
saveInterval = 1000
printInterval = 100
trainIters = 1000000

learningRate = 1e-4
betas = (0.9, 0.95)
epsilon = 1e-8
weight_decay = 0.1


x, y = getBatch(split="train")



	# print(row.tolist())
# print(len(x))
# print(len(x[0]))
# print(t.fromBytes(t.decode(x[0].tolist())))
# print()
# print(t.fromBytes(t.decode(y[0].tolist())))
# print()
# print(t.fromBytes(t.decode(x[1].tolist())))
# print()
# print(t.fromBytes(t.decode(y[1].tolist())))
# print()
# print(t.fromBytes(t.decode(x[2].tolist())))
# print()
# print(t.fromBytes(t.decode(y[2].tolist())))
# print()
#
# input()

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

		xp = self.posEmbed(torch.arange(0, min(len(x[0]), blockSize), device = device))
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
				# print(i)
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
	return torch.load("model.pth", weights_only = False, map_location=device)








model = Model().to(device)
optimizer = torch.optim.AdamW(model.parameters(), lr = learningRate, betas=betas, weight_decay=weight_decay,eps=epsilon,)
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
	# print("\rbatch", end="")
	x, y = getBatch()
	optimizer.zero_grad(set_to_none=True)
	with torch.autocast(device_type="cuda", dtype=torch.bfloat16):
		# print("\rforward", end="")
		logits, loss = model(x, y)
		# print("\rbackward", end="")
		loss.backward()
	optimizer.step()

	if step % evalInterval == 0 and step != 0:
		print(step, model.estimateLoss())
	if step % saveInterval == 0 and step != 0:
		save(model, optimizer, step)
		print(f"saved at step {step}, pointers: {trainPointer}, {valPointer}, {time.ctime()}")
	if step % printInterval == 0:
		print(f"step {step}")
	step += 1

print("done!")
save(model, optimizer, step)
print(model.estimateLoss())
g = model.generate(encode("Why did the chicken cross the road?").to(device), 1000).cpu().tolist()
print(t.fromBytes(t.decode(g)))



# print(getBatch())