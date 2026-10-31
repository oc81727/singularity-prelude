import heapq, json, re, time, array
import math


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
		self.bannedStart = set(list(range(256, 256 + len(self.special))) + [ord(i) for i in ["\n"]])
		self.bannedEnd = set(list(range(256, 256 + len(self.special))) + [ord(i) for i in [" ", "\n"]])
		self.heap = []
		self.defaultTokenSize = self.vocabSize
		# self.pairs = {}
		self.versions = {}


	def encodePair2(self, v1, v2):
		return v1 << 16 | v2

	def decodePair2(self, enc):
		return enc >> 16, enc & 0xffff



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




	def splitSpecialTokens(self, text): 
		special = re.findall(self.customSplit, text)
		special.append("")
		segs = re.split(self.customSplit, text)
		n = 0
		while n < len(segs):
			yield (segs[n], special[n]) 
			n += 1
		





	def printArr(self, arr):
		print("-")
		l = 10
		for i in range(math.ceil(len(arr) / l)):
			print(i, arr[i*l:(i+1)*l])
		print("-")




	def addPair(self, pairs, v1, v2, n, pairIndex):
		enc = self.encodePair2(v1, v2)
		# print(f"adding pair {enc}")
		if not enc in pairs:
			pairs[enc] = array.array("i") # packed array (not python lists that uses pointers), O(1) appends (most of the time)
			self.versions[enc] = 0
			self.pairLengths[enc] = 1
		else:
			self.versions[enc] += 1
			self.pairLengths[enc] += 1
		pairIndex[n] = len(pairs[enc])
		# maps a bytes index to its position in its corresponding pairs array
		# to go from byteArray index to pair:
		# find enc
		# pairs[enc][pairIndex[index]]
		pairs[enc].append(n)



	def getPairs(self, byteArray, pairIndex):
		pairs = {}
		for n in range(len(byteArray) - 1):
			self.addPair(pairs, byteArray[n], byteArray[n+1], n, pairIndex)
		return pairs

	def reHeap(self, pairs):
		self.heap = [(-len(pairs[p]), self.versions[p], p) for p in pairs if len(pairs[p]) > 0]
		heapq.heapify(self.heap)


	def build(self, num, checkpoints = None):
		self.versions = {}
		self.pairLengths = {}
		num -= self.defaultTokenSize
		print(f"iterations: {num}")
		print("starting build")
		by = self.toBytes(self.corpus)
		byteLength = len(by)
		print(f"byteLength: {byteLength}")
		byteArray = np.array(by, dtype=np.int32)

		nextIndex = np.arange(1, byteLength + 1, dtype=np.int32)
		nextIndex[-1] = -1
		prevIndex = np.arange(-1, byteLength-1, dtype=np.int32)
		pairIndex = np.zeros(byteLength, dtype=np.int32) # pairPointer
		# can be byteLength -1 but who cares :p
		print("getting pairs")
		pairs = self.getPairs(byteArray, pairIndex)
		print("building heap")
		self.heap = []
		for p in pairs:
			heapq.heappush(self.heap, (-len(pairs[p]), self.versions[p], p)) # (-length, version, pairEncoding)
			# replace with single packed integer to increase rebuild speed, if bothered

		for i in range(num):
			if len(self.heap) > 400 * len(pairs):
				# print(f"pairs length: {len(pairs)}")
				s = time.time()
				# print("reheaping frfr")
				# print(f"heap length: {len(self.heap)}")
				self.reHeap(pairs)
				# print(f"reheap done in {time.time() - s}")
				# print(f"heap length: {len(self.heap)}")
			if i % 50 == 0:
				print(f"iter {i}")
				# self.report_memory(byteArray, nextIndex, prevIndex, pairIndex, pairs)
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
				v1, v2 = self.decodePair2(heapTop[2])
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

			for curr in toProcess: # loop through current pair occurences
				if curr == -1: # skip if invalidated
					continue
				pre = prevIndex[curr]
				currVal = byteArray[curr]
				post = nextIndex[curr]
				postPost = nextIndex[post] if post != -1 else -1
				if pre != -1:
					enc = self.encodePair2(byteArray[pre], byteArray[curr])
					pairs[enc][pairIndex[pre]] = -1 # invalidating pair occurence
					if enc != currentEnc:
						self.versions[enc] += 1
						heapq.heappush(self.heap, (-len(pairs[enc]), self.versions[enc], enc))
					self.pairLengths[enc] -= 1
					if self.pairLengths[enc] == 0:
						del pairs[enc]
				if post != -1 and postPost != -1: # should be postpost
					enc = self.encodePair2(byteArray[post], byteArray[postPost])
					pairs[enc][pairIndex[post]] = -1 # invalidating pair occurence
					if enc != currentEnc:
						self.versions[enc] += 1
						heapq.heappush(self.heap, (-len(pairs[enc]), self.versions[enc], enc))
					self.pairLengths[enc] -= 1
					if self.pairLengths[enc] == 0:
						del pairs[enc]

				if currVal in self.bannedEnd:
					self.bannedEnd.add(newToken)
				if byteArray[post] in self.bannedStart:
					self.bannedStart.add(newToken)

				# remove right of current pair
				byteArray[post] = -1
				prev = prevIndex[post]
				nex = nextIndex[post]
				if prev != -1:
					nextIndex[prev] = nex
				if nex != -1:
					prevIndex[nex] = prev
				nextIndex[post] = -1
				prevIndex[post] = -1
				# setting new token value
				byteArray[curr] = newToken

				# creating new pairs
				if pre != -1:
					enc = self.encodePair2(byteArray[pre], byteArray[curr]) # a waste to recalc, but whatevs
					self.addPair(pairs, byteArray[pre], byteArray[curr], pre, pairIndex)
					heapq.heappush(self.heap, (-len(pairs[enc]), self.versions[enc], enc))
				post = nextIndex[curr]
				if post != -1:
					enc = self.encodePair2(byteArray[curr], byteArray[post])
					self.addPair(pairs, byteArray[curr], byteArray[post], curr, pairIndex)
					heapq.heappush(self.heap, (-len(pairs[enc]), self.versions[enc], enc))
		self.mergesInv = {v: self.decodePair2(k) for k, v in self.merges.items()}



		print("\ndone!")

	def encode(self, text):
		# print("starting encode")
		self.versions = {}
		self.pairLengths = {}
		by = self.toBytes(text)
		byteLength = len(by)
		byteArray = np.array(by, dtype=np.int32)

		nextIndex = np.arange(1, byteLength + 1, dtype=np.int32)
		nextIndex[-1] = -1
		prevIndex = np.arange(-1, byteLength - 1, dtype=np.int32)
		# print(nextIndex)
		pairIndex = np.zeros(byteLength, dtype=np.int32)  # pairPointer
		# can be byteLength -1 but who cares :p

		# alive = np.ones(byteLength, dtype=np.bool)
		# print("getting pairs")
		# self.printArr(pairIndex)
		pairs = self.getPairs(byteArray, pairIndex)
		# print("building heap")
		self.heap = []
		invalid = -99999.5
		for p in pairs:
			heapq.heappush(self.heap, (self.merges.get(p, invalid), self.versions[p], p))  # (-length, version, pairEncoding)

		while True:
			b = False
			while True:
				if len(self.heap) == 0:
					b = True
					# print("no more merges!")
					break
				heapTop = heapq.heappop(self.heap)
				if self.versions[heapTop[2]] != heapTop[1]:
					continue  # invalid version
				if heapTop[0] == invalid:
					continue
				# v1, v2 = self.decodePair(heapTop[2])
				# if (v1 in self.bannedStart or v2 in self.bannedEnd):
				# 	continue  # banned pair
				break
			if b:
				break
			currentEnc = heapTop[2]
			token = heapTop[0]

			toProcess = pairs[currentEnc]

			for curr in toProcess:  # loop through current pair occurences
				if curr == -1:  # skip if invalidated
					continue
				# curr is index of byteArray

				# remove occurences of pre and post pair
				pre = prevIndex[curr]
				currVal = byteArray[curr]
				post = nextIndex[curr]
				postPost = nextIndex[post] if post != -1 else -1
				if pre != -1:
					enc = self.encodePair2(byteArray[pre], byteArray[curr])
					pairs[enc][pairIndex[pre]] = -1  # invalidating pair occurence
					if enc != currentEnc:
						self.versions[enc] += 1
						heapq.heappush(self.heap, (self.merges.get(enc, invalid), self.versions[enc], enc))
				if post != -1 and postPost != -1:  # should be postpost
					enc = self.encodePair2(byteArray[post], byteArray[postPost])
					pairs[enc][pairIndex[post]] = -1  # invalidating pair occurence
					if enc != currentEnc:
						self.versions[enc] += 1
						heapq.heappush(self.heap, (self.merges.get(enc, invalid), self.versions[enc], enc))



				# remove right of current pair
				byteArray[post] = -1
				prev = prevIndex[post]
				nex = nextIndex[post]
				if prev != -1:
					nextIndex[prev] = nex
				if nex != -1:
					prevIndex[nex] = prev
				nextIndex[post] = -1
				prevIndex[post] = -1
				# setting new token value
				byteArray[curr] = token

				# creating new pairs
				if pre != -1:
					enc = self.encodePair2(byteArray[pre], byteArray[curr])  # a waste to recalc, but whatevs
					self.addPair(pairs, byteArray[pre], byteArray[curr], pre, pairIndex)
					heapq.heappush(self.heap, (self.merges.get(enc, invalid), self.versions[enc], enc))
				post = nextIndex[curr]
				if post != -1:
					enc = self.encodePair2(byteArray[curr], byteArray[post])
					self.addPair(pairs, byteArray[curr], byteArray[post], curr, pairIndex)
					heapq.heappush(self.heap, (self.merges.get(enc, invalid), self.versions[enc], enc))
		# print(byteArray)
		# input()



		index = 0
		t = [int(byteArray[index])]
		while nextIndex[index] != -1:
			index = nextIndex[index]
			t.append(int(byteArray[index]))
		return t





	def save(self, name = ""):
		with open(f"{name}.json", "w", encoding="utf-8") as f:
			json.dump({"merges":{int(k): v for k,v in self.merges.items()}, "bannedStart": sorted(list(self.bannedStart)), "bannedEnd": sorted(list(self.bannedEnd))}, f, indent=2)

	def load(self, name = ""):
		with open(f"{name}.json", "r", encoding="utf-8") as f:
			data = json.load(f)
			self.merges = {np.int32(k):v for k, v in data["merges"].items()}
			self.mergesInv = {v:self.decodePair2(k) for k,v in self.merges.items()}

			self.bannedStart = set(data["bannedStart"])
			self.bannedEnd = set(data["bannedEnd"])



t = Tokenizer()

t.load("data/tiktoks/converted32768")
# t.merges = {k:v for n, (k,v) in enumerate(t.merges.items()) if n < 400}
t.loadText("data/combined_clean2.txt")
print(t.encode(t.corpus))



