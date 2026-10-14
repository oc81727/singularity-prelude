from bigT import Tokenizer
from datasets import load_dataset



t = Tokenizer()
t.load("data/tiktoks/newtokens32768")

dataset = load_dataset(
	"data/paraqeet/iliketrains",
	data_files="*.parquet",
	split="train",
	streaming=True,
)

n = 0
# will take around 2 days to finish running...
for example in dataset:
	t.encode(example["text"])
	n += 1
	if n%100 == 0:
		print(n)