import heapq, json, re, time, array

from linkedin import LinkedList, LinkedNode


import numpy as np




class Tokenizer():
	def __init__(self):
		self.corpus = ""
		self.bytes = []
		self.merges = {}
		self.mergesInv = {}
		self.safeDistance = 1000000
		self.special = ["<|nameStart|>", "<|nameEnd|>", "<|msgStart|>", "<|msgEnd|>", "<|endOfDocument|>"]
		self.customSplit = "|".join([i.replace("|", "\\|") for i in self.special])
		self.customReplace = {self.special[n]: 256+n for n in range(len(self.special))} # token to id
		self.customReplaceInv = {v:k for k,v in self.customReplace.items()} # id to token
		self.vocabSize = 256 + len(self.special)
		self.bannedStart = list(range(256, 256 + len(self.special))) + [ord(i) for i in ["\n"]]
		self.bannedEnd = list(range(256, 256 + len(self.special))) + [ord(i) for i in [" ", "\n"]]
		self.heap = []
		self.defaultTokenSize = self.vocabSize
		# self.pairs = {}
		self.versions = {}

	def encodePair(self, v1, v2): # can use shifting and packing instead, not that im bothered to ofc
		return v1 * self.safeDistance + v2

	def decodePair(self, enc):
		v1 = enc // self.safeDistance
		v2 = enc % self.safeDistance
		return v1, v2



	def loadText(self, name):
		with open(name, "r", encoding="utf-8") as f:
			self.corpus = f.read()

	def toBytes(self, text):
		by = []
		for seg in list(self.splitSpecialTokens(text)):
			by.extend(list(bytearray(seg[0], "utf-8")))
			if seg[1] != "":
				by.append(self.customReplace[seg[1]])
		return by



	def splitSpecialBytes(self, by):
		g = []
		n = 0
		while n < len(by):
			b = by[n]
		# for b in by:
			if b in self.customReplaceInv:
				n += 1
				yield (g, self.customReplaceInv[b])
				g = []
			if n >= len(by):
				break
			b = by[n]
			g.append(b)

			n += 1
		yield (g, "")

	def splitSpecialBytes2(self, by):
		g = []
		out = []
		for b in by:
			if b in self.customReplaceInv:
				out.append((g, self.customReplaceInv[b]))
				g = []
			else:
				g.append(b)
		out.append((g, ""))
		return out


	def splitSpecialTokens(self, text): 
		special = re.findall(self.customSplit, text)
		special.append("")
		segs = re.split(self.customSplit, text)
		n = 0
		while n < len(segs):
			yield (segs[n], special[n]) 
			n += 1
		

	def fromBytes(self, by):
		# print("converting")
		text = []
		# print(self.splitSpecialBytes2(by))
		for seg in self.splitSpecialBytes2(by):
			# print(seg)
			text.append(bytes(seg[0]).decode("utf-8", errors="replace"))
			text.append(seg[1])
		return "".join(text)



	def popnSwap(self, arr, index):
		arr[index] = arr[-1]
		arr.pop()


	def addPair(self, pairs, v1, v2, n, pairIndex):
		enc = self.encodePair(v1, v2)
		if not enc in pairs:
			pairs[enc] = array.array("i") # packed array (not python lists that uses pointers), O(1) appends (most of the time)
			self.versions[enc] = 0
		else:
			self.versions[enc] += 1
		pairIndex[n] = len(pairs[enc])
		# to go from byteArray index to pair:
		# find enc
		# pairs[enc][pairIndex[index]]
		pairs[enc].append(n)



	def getPairs(self, byteArray, pairIndex):
		pairs = {}
		for n in range(len(byteArray) - 1):
			self.addPair(pairs, byteArray[n], byteArray[n+1], n, pairIndex)
		return pairs














	def build(self, num, checkpoints = None):
		num -= self.defaultTokenSize
		print(f"iterations: {num}")
		print("starting build")
		print("constructing linked list")
		by = self.toBytes(self.corpus)
		byteLength = len(by)
		byteArray = np.array(by, dtype=np.int32)

		nextIndex = np.arange(byteLength, dtype=np.int32)
		nextIndex[:-1] = -1
		prevIndex = np.arange(-1, byteLength, dtype=np.int32)
		pairIndex = np.zeros(byteLength, dtype=np.int32) # pairPointer
		# can be byteLength -1 but who cares :p

		alive = np.ones(byteLength, dtype=np.bool)

		print("getting pairs")
		pairs = self.getPairs(byteArray, pairIndex)
		print("building heap")
		self.heap = []
		for p in pairs:
			heapq.heappush(self.heap, (-len(pairs[p]), self.versions[p], p)) # (-length, version, pairEncoding)

		for i in range(num):
			print(f"iter {i}")
			b = False
			while True:
				if len(self.heap) == 0:
					b = True
					print("no more merges!")
					break
				heapTop = heapq.heappop(self.heap)
				if self.versions[heapTop[2]] != heapTop[1]:
					continue # invalid version
				if heapTop[0] == 0:
					continue
				v1, v2 = self.decodePair(heapTop[2])
				if (v1 in self.bannedStart or v2 in self.bannedEnd):
					continue # banned pair
				break
			if b:
				break

			currentEnc = heapTop[2]
			newToken = self.vocabSize
			self.vocabSize += 1
			self.merges[currentEnc] = newToken

			toProcess = pairs[currentEnc]

			for curr in toProcess:
				# curr is index of byteArray
				
				# remove occurences of pre and post pair
				pre = prevIndex[curr]
				post = nextIndex[curr]
				if prevIndex[curr] != -1:
					enc = self.encodePair(byteArray[pre], byteArray[curr])
					pairs[enc][pairIndex[pre]]



		


	def getOccurences(self, textBytes):
		occ = {}
		curr = textBytes.start
		while True:
			if not curr.value in occ:
				occ[curr.value] = LinkedList()
			occ[curr.value].append(curr)

			if curr.next is not None:
				curr = curr.next
			else:
				return occ


	def decode(self, by):
		# print("decoding")
		textBytes = LinkedList()
		textBytes.setList(by)
		# for decoding, replace pairs in order of token value, descending order
		occurences = self.getOccurences(textBytes)
		


		for merge in reversed(self.mergesInv.keys()): # loop for replacing each token
			if not merge in occurences:
				continue

			v1 = self.mergesInv[merge][0]
			v2 = self.mergesInv[merge][1]

			toProcess = occurences[merge]
			curr = toProcess.start
			# curr.value is the node in textBytes
			while True: # loop deal with all occurences of this token
				# print(curr)
				# input()
				curr.value.value = v1
				textBytes.insert(curr.value, v2)

				if not v1 in occurences:
					occurences[v1] = LinkedList()
				occurences[v1].append(curr.value)
				if not v2 in occurences:
					occurences[v2] = LinkedList()
				occurences[v2].append(curr.value.next)






				if curr.next is not None:
					curr = curr.next
				else:
					break

		# print("done!")
		# print(textBytes)
		# l = textBytes.toList()
		# print(l)
		# print(self.fromBytes(l))
		return textBytes.toList()

	def visualize(self, by):
		for n in range(len(by)):
			by[n] = self.fromBytes(self.decode([by[n]]))
		return "|".join(by)

	def save(self, name = ""):
		with open(f"{name}.json", "w", encoding="utf-8") as f:
			json.dump({"merges":self.merges, "bannedStart": self.bannedStart, "bannedEnd": self.bannedEnd}, f, indent=2)

	def load(self, name = ""):
		with open(f"{name}.json", "r", encoding="utf-8") as f:
			data = json.load(f)
			self.merges = {int(k):v for k, v in data["merges"].items()}
			self.mergesInv = {v:self.decodePair(k) for k,v in self.merges.items()}

			self.bannedStart = data["bannedStart"]
			self.bannedEnd = data["bannedEnd"]






		



t = Tokenizer()


# with open("data/combined_sample.txt", encoding="utf-8") as f:
# 	t.corpus = f.read()
# t.build(32768, checkpoints = [8192, 16384])
# t.save("newtokens32768")
# starting at 14:39 (on laptop!)
# maxing out my poor laptops ram
# going crazy on virtual memory rn
# never mind ill just run it on my pc later


# started at 4:28
# finished at 5:09

# t.corpus = """represents low in ASCII-compatible UTF-8.
# For each sequence, maintain metadata:
# start: first active node.
# end: last active node.
# length: number of active nodes.
# Every node should also contain:
# value: current token ID.
# prev and next: links to adjacent nodes.
# pointer: the occurrence-list node for the pair starting at this node, or None.
# active: whether the node is still part of the sequence.
# The active flag is useful for defensive validation, particularly when handling stale references.
# 2.3 Optionally compress repeated sequences
# If the corpus contains many duplicate segments, count how frequently each distinct sequence appears."""
# t.corpus="hellolo"
t.corpus = "hello<|nameStart|>john<|nameEnd|><|msgStart|>world frfr testing aha im gonna kms woah who said that why did u say that the lion and the witch and the wardrobe foo bar antimony arsenic aluminum selenium hydrogen oxygen nitrogen rhenium nickel neodymium neptunium germanium iron americium ruthenium uranium europium zirconium lutetium vanadium lanthanum<|msgEnd|>"


# with open("swift.txt", encoding="utf-8") as f:
	# t.corpus = f.read()

# t.load("tokens32768")


# t.encode(t.corpus[:100])

t.build(270)
# print(t.fromBytes(t.decode(t.encode(t.corpus[:1000]))))
# t.save("debug")
# print(t.visualize())
# print(t.corpus)
# # print(t.fromBytes(t.decode(t.encode(t.corpus))))
# print(t.visualize(t.encode(t.corpus)))