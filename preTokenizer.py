from bigT2 import Tokenizer
from datasets import load_dataset
import time


t = Tokenizer()
# t.load("data/tiktoks/converted32768")
t.load("data/tiktoks/checkpoint7931")

dataset = load_dataset(
	"data/paraqeet/iliketrains",
	data_files="*.parquet",
	split="train",
	streaming=True,
)

n = 0
# will take around 2 days to finish running...
s = time.time()
l = 0
for example in dataset:
	l += len(t.encode(example["text"]))
	n += 1
	if n%100 == 0:
		print(n)
		print(time.time() - s)
		print(l)
	if n == 1000:
		break