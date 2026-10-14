from datasets import load_dataset

dataset = load_dataset(
    "data/paraqeet",
    data_files="*.parquet",
    split="train",
    streaming=True,
)

with open("sample.txt", "a", encoding="utf-8") as f:
	n = 0
	for example in dataset:
		n += 1
		f.write(example["text"])
		if n == 20000:
			break