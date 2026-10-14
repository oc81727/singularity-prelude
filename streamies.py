# from datasets import load_dataset
#
# dataset = load_dataset(
#     "data/paraqeet/iliketrains",
#     data_files="*.parquet",
#     split="train",
#     streaming=True,
# )
#
# print(dataset)
# for example in dataset:
# 	print(example["text"])
# 	input()


import glob
import pyarrow.parquet as pq

files = glob.glob("data/paraqeet/valorant/*.parquet")

total_rows = sum(
    pq.ParquetFile(file).metadata.num_rows
    for file in files
)

print("Total rows:", total_rows)