# with open("../data/paraqeet/iliketrains/txt/1.5.txt", encoding="utf-8") as f:
# 	t = f.read()[:10000000]
# with open("../data/paraqeet/iliketrains/txt/1.txt","w", encoding="utf-8") as f:
# 	f.write(t)

import numpy as np

from bigT2 import Tokenizer

n = np.fromfile("../data/paraqeet/iliketrains/bin/2.bin", dtype=np.uint16)
#
with open("../data/paraqeet/iliketrains/txt/1.txt", encoding="utf-8") as f:
# 	t = f.read()[:1000]
# with open("../data/paraqeet/iliketrains/txt/1.txt","w", encoding="utf-8") as f:
# 	f.write(t)
	print(f.read()[:1000])
	# print(list(f.read()[:1000].encode("utf8")))
print(n.shape)
print(n[:1000])

t = Tokenizer()
t.load("../data/tiktoks/checkpoint7931")
b = t.decode(n[:1000].tolist())
print(b)
print(t.fromBytes(b))

print(t.fromBytes(t.decode([2272, 2272, 256, 106, 4114, 257, 258, 5404, 1027, 259, 260, 2272, 2272])))