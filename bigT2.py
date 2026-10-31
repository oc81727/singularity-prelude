import heapq, json, re, time

from linkedin import LinkedList, LinkedNode






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

	def encodePair(self, v1, v2):
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


	def addPair(self, pairs, b1, b2):
		enc = self.encodePair(b1.value, b2.value)
		if not enc in pairs:
			pairs[enc] = LinkedList()
			self.versions[enc] = 0
		else:
			self.versions[enc] += 1
		pairs[enc].append(b1)
		b1.pairPointer = pairs[enc].end



	def getPairs(self, textBytes):
		pairs = {}
		l = textBytes.length
		for n, node in enumerate(textBytes.loop()):
			if n == l - 1:
				break # dont process last byte, bc it has no next
			self.addPair(pairs, node, node.next)
			# enc = self.encodePair(node.value, node.next.value)
			# if not enc in pairs:
			# 	pairs[enc] = LinkedList()
			# pairs[enc].append(node)
			# node.pairPointer = pairs[enc].end
		return pairs












	def build(self, num, checkpoints = None):
		print("starting build")
		print("constructing linked list")
		textBytes = LinkedList()
		textBytes.setList(self.toBytes(self.corpus))
		# print(textBytes)
		print("getting pairs")
		pairs = self.getPairs(textBytes)
		print("building heap")
		self.heap = []
		for p in pairs:
			heapq.heappush(self.heap, (-pairs[p].length, self.versions[p], p)) # (-length, version, pairEncoding)
		# print(pairs)
		# print(textBytes)
		# print(self.heap)


		# print(f"versions: {self.versions}")
		# print("beginning main loop")
		print("starting")
		for i in range(num - self.defaultTokenSize):
			# print(textBytes)
			if checkpoints is not None and i + self.defaultTokenSize in checkpoints:
				self.save(f"checkpoint{i}")
				print(f"\nsaved checkpoint {i}\n")

			
			# print(f"heap: {self.heap}")
			b = False
			while True:
				if len(self.heap) == 0:
					print("no more available merges!")
					b = True
					break
				heapCommon = heapq.heappop(self.heap) # add version check
				# print(f"processing {heapCommon}")
				if heapCommon[1] != self.versions[heapCommon[2]]: # check version
					# print("outdated version")
					continue

				v1, v2 = self.decodePair(heapCommon[2])
				if (v1 in self.bannedStart or v2 in self.bannedEnd):
					# print("banned")
					continue

				if pairs[heapCommon[2]].length == 0:
					# print("0 length")
					continue
				break
					
			# print(heapCommon)
			# print(pairs[heapCommon[2]].length)
			if b:
				break
			if i%50 == 0:
				print(f"\riter {i}, {v1}-{v2} {-heapCommon[0]}       ", end="")
			commonPair = heapCommon[2]
			newToken = self.vocabSize
			self.vocabSize += 1
			self.merges[commonPair] = newToken
			# print(f"{newToken} {commonPair}")
			# processing pair occurences
			toProcess = pairs[commonPair]
			# curr.value is the actual pair
			for curr in toProcess.loop():
				# curr.value is the node in bytes list
				# print(f"currently removing for {curr}")
				p = curr.value
				# removing occurences
				if p.prev is not None: # not at start
					# remove occurence of previous pair
					affected = p.prev.pairPointer
					affected.parent.removeNode(affected)

					enc = self.encodePair(affected.value.value, affected.value.next.value)
					if enc != commonPair: # dont add new versions/heap entries for the pair currently being worked on, or it will run again for the same enc
						self.versions[enc] += 1
						heapq.heappush(self.heap, (-pairs[enc].length, self.versions[enc], enc))
				if p.next.next is not None: # not at end
					affected = p.next.pairPointer
					affected.parent.removeNode(affected)

					enc = self.encodePair(affected.value.value, affected.value.next.value)
					if enc != commonPair:
						self.versions[enc] += 1
						heapq.heappush(self.heap, (-pairs[enc].length, self.versions[enc], enc))


				if newToken not in self.bannedEnd and p.value in self.bannedEnd:
					self.bannedEnd.append(newToken)
				if newToken not in self.bannedStart and p.next.value in self.bannedStart:
					self.bannedStart.append(newToken)

				# removing right of current pair
				textBytes.removeNode(p.next) # removing from bytes list

				# merging, replacing left with new value
				p.value = newToken

				# creating new pairs
				if p.prev is not None:
					self.addPair(pairs, p.prev, p)
					enc = self.encodePair(p.prev.value, p.value)
					heapq.heappush(self.heap, (-pairs[enc].length, self.versions[enc], enc))
				if p.next is not None: # right has been removed, left now connects to the byte after
					self.addPair(pairs, p, p.next)
					enc = self.encodePair(p.value, p.next.value)
					heapq.heappush(self.heap, (-pairs[enc].length, self.versions[enc], enc))


		self.mergesInv = {v:self.decodePair(k) for k,v in self.merges.items()}
		print("\ndone!")
		print(textBytes)
		# return textBytes.toList()


	def encode(self, text):
		textBytes = LinkedList()
		textBytes.setList(self.toBytes(text))
		# for encoding, replace pairs in order of token value, ascending order
		self.versions = {}
		pairs = self.getPairs(textBytes)
		self.heap = []
		invalid = 99999.5
		for p in pairs:
			heapq.heappush(self.heap, (self.merges.get(p, invalid), self.versions[p], p)) # (value, enc)
		



		while True: # loop for replacing each token pair
			isDone = False
			while True: # loop for grabbing current token pair from heap
				if len(self.heap) == 0:
					isDone = True
					break
				current = heapq.heappop(self.heap)
				# print(f"processing {current}")
				if current[0] != invalid:
					if current[1] != self.versions[current[2]]:
						# print("invalid version")
						pass
					else:
						break
				else:
					pass
					# print("unknown merge pair")
			if isDone:
				break

			currentPair = current[2]
			token = current[0]

			toProcess = pairs[currentPair]


			if toProcess.length > 0:
				curr = toProcess.start




				# curr.value is the actual pair


				# print("starting loop")
				# while True: # loop deal with all occurences of this pair
				for curr in toProcess.loop():
					# print("inner iteration")
					# print(f"bytes: {textBytes}")
					# print(f"current: {curr}")
					# print(f"p2: {curr}")
					p = curr.value
					# print(p)
					# removing occurences
					if p.prev is not None: # not at start
						# print(f"not at start")
						# remove occurence of previous pair
						affected = p.prev.pairPointer
						# print(f"removing {affected}")
						affected.parent.removeNode(affected)

						enc = self.encodePair(affected.value.value, affected.value.next.value)
						if enc != currentPair:
							self.versions[enc] += 1
							heapq.heappush(self.heap, (self.merges.get(enc, invalid), self.versions[enc], enc))
					if p.next.next is not None: # not at end
						affected = p.next.pairPointer
						# print("not at end")
						# print(f"removing {affected}")
						affected.parent.removeNode(affected)

						enc = self.encodePair(affected.value.value, affected.value.next.value)
						if enc != currentPair:
							self.versions[enc] += 1
							heapq.heappush(self.heap, (self.merges.get(enc, invalid), self.versions[enc], enc))


					# removing right of current pair
					# print(f"removing node {p.right}")
					textBytes.removeNode(p.next)
					# p.right.remove() # removing from bytes list

					# merging, replacing left with new value
					p.value = token

					# print(f"bytes now: {textBytes}")
					# creating new pairs
					# print("creating new pairs")
					if p.prev is not None:
						# print("not at start")
						# print(f"making pair with {p.left.prev}, {p.left}")
						self.addPair(pairs, p.prev, p)
						enc = self.encodePair(p.prev.value, p.value)
						heapq.heappush(self.heap, (self.merges.get(enc, invalid), self.versions[enc], enc))
					if p.next is not None: # right has been removed, left now connects to the byte after
						# print("not at end")
						# print(f"making pair with {p.left}, {p.left.next}")
						self.addPair(pairs, p, p.next)
						enc = self.encodePair(p.value, p.next.value)
						heapq.heappush(self.heap, (self.merges.get(enc, invalid), self.versions[enc], enc))
					






					

		# print("done!")
		# print(textBytes)
		return textBytes.toList()


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






		



# t = Tokenizer()
# t.load("data/tiktoks/newtokens32768")
#
# d = [2482, 323, 384, 416, 289, 10151, 32, 2619, 384, 289, 12118, 365, 262, 9541, 1003, 6959, 350, 419, 3274, 1275, 478, 746, 416, 534, 503, 294, 268, 2748, 9928, 449, 315, 2868, 289, 27849, 44, 318, 363, 2289, 294, 4217, 7161, 839, 578, 5596, 292, 788, 268, 315, 3202, 289, 10912, 268, 4960, 2195, 482, 315, 3260, 621, 391, 490, 835, 8617, 293, 21395, 1618, 264, 954, 492, 68, 24045, 19287, 314, 2611, 5839, 268, 1565, 621, 622, 630, 677, 528, 289, 3263, 15209, 10, 17647, 14224, 2760, 315, 1688, 738, 289, 268, 9892, 283, 9273, 371, 866, 614, 102, 2259, 1840, 606, 315, 284, 24670, 114, 936, 3360, 1235, 499, 268, 1920, 1210, 2822, 562, 622, 262, 8968, 528, 328, 5168, 292, 3045, 807, 262, 844, 292, 262, 7111, 19736, 365, 289, 2369, 289, 13960, 46, 948, 357, 6394, 807, 1850, 268, 3452, 292, 349, 553, 2055, 3531, 16939, 2939, 596, 289, 472, 9249, 622, 289, 2127, 5689, 46, 788, 1688, 738, 289, 2124, 2614, 349, 3286, 738, 293, 3856, 292, 788, 30893, 292, 1688, 738, 900, 268, 3452, 46, 8284, 10, 73, 391, 8722, 328, 2040, 482, 349, 6882, 578, 289, 268, 738, 4085, 292, 18719, 328, 807, 289, 541, 3773, 771, 3925, 503, 328, 262, 1048, 289, 743, 336, 20878, 1224, 6783, 2557, 771, 391, 1271, 292, 268, 738, 9133, 3045, 454, 262, 4617, 326, 262, 552, 349, 391, 292, 349, 622, 289, 962, 492, 68, 429, 5402, 194, 172, 73, 629, 598, 315, 30988, 268, 12557, 391, 25797, 881, 268, 1541, 564, 292, 2139, 289, 962, 1552, 482, 349, 3899, 7513, 292, 549, 3468, 648, 2513, 1533, 292, 549, 18880, 555, 264, 7375, 292, 549, 14917, 4824, 326, 549, 12492, 22185, 900, 23695, 289, 985, 349, 839, 289, 549, 827, 11648, 292, 4400, 549, 26400, 13969, 1198, 121, 622, 12972, 289, 534, 289, 268, 305, 28176, 1763, 460, 330, 2856, 292, 289, 743, 608, 349, 1289, 405, 1717, 2319, 384, 386, 4878, 294, 1686, 621, 391, 268, 600, 1255, 1349, 7845, 1238, 293, 472, 14265, 292, 315, 2678, 1850, 268, 10685, 350, 268, 534, 4033, 10, 73, 3843, 419, 16312, 338, 292, 4872, 22356, 350, 6131, 3438, 370, 659, 391, 619, 336, 349, 4990, 1511, 503, 289, 2516, 350, 268, 9830, 9449, 294, 268, 327, 70, 22060, 292, 11279, 326, 262, 4844, 292, 2078, 8731, 4792, 771, 295, 14117, 697, 807, 326, 528, 292, 10052, 503, 336, 1552, 292, 268, 5211, 2365, 289, 405, 549, 3468, 326, 350, 1219, 341, 391, 619, 289, 2678, 697, 268, 6019, 315, 5752, 3740, 5168, 457, 268, 8016, 349, 7124, 336, 349, 796, 405, 2524, 1138, 8647, 578, 268, 2243, 292, 3511, 508, 390, 587, 46, 508, 18508, 503, 549, 2150, 1078, 5168, 292, 1374, 771, 416, 3260, 5168, 508, 6125, 15949, 46, 771, 696, 2878, 349, 10137, 807, 289, 268, 8774, 292, 3040, 900, 512, 357, 7802, 860, 508, 3040, 900, 697, 662, 293, 268, 7919, 771, 9598, 336, 349, 2994, 262, 3635, 2140, 268, 1082, 294, 807, 268, 3272, 9090, 293, 336, 13188, 292, 4983, 391, 3899, 9436, 3584, 1956, 807, 671, 598, 3892, 326, 268, 4762, 866, 733, 3521, 2820, 662, 292, 26347, 10083, 293, 549, 1662, 350, 268, 15507, 292, 315, 5252, 503, 294, 336, 2247, 1576, 553, 798, 268, 5757, 292, 12576, 46, 408, 1282, 2400, 2055, 292, 1541, 7890, 697, 549, 10299, 4434, 349, 6009, 289, 454, 292, 349, 3899, 503, 289, 740, 549, 2650, 3168, 293, 268, 6019, 289, 807, 25723, 490, 18868, 1545, 10, 73, 391, 738, 289, 927, 262, 3584, 22992, 606, 349, 391, 3752, 293, 24253, 606, 429, 4541, 391, 621, 387, 268, 11169, 46, 315, 7895, 807, 365, 2714, 289, 893, 677, 349, 391, 1200, 46, 315, 391, 6492, 478, 2086, 315, 622, 289, 12849, 292, 472, 3844, 648, 1102, 387, 268, 619, 606, 315, 5738, 807, 896, 292, 788, 315, 12969, 662, 528, 294, 472, 797, 2336, 292, 797, 294, 807, 328, 1278, 21911, 1860, 349, 391, 326, 472, 930, 621, 391, 677, 13586, 1116, 341, 391, 2524, 16850, 315, 746, 416, 1042, 315, 25629, 9527, 2820, 5168, 482, 315, 391, 5532, 294, 10418, 294, 18148, 315, 20010, 328, 472, 3261, 438, 15853, 315, 391, 1186, 1011, 289, 12509, 315, 1669, 350, 262, 14086, 292, 315, 391, 31318, 315, 391, 1268, 2667, 350, 268, 2081, 552, 391, 472, 23192, 349, 391, 326, 268, 31241, 771, 622, 630, 326, 268, 4762, 446, 2015, 490, 349, 391, 1078, 292, 5738, 363, 14027, 3022, 2283, 387, 268, 6230, 621, 391, 677, 5853, 2086, 10, 7926, 8963, 622, 17987, 1007, 1623, 978, 349, 1840, 4501, 93, 1416, 391, 262, 1763, 866, 315, 9234, 3821, 771, 746, 416, 629, 608, 315, 622, 1268, 2513, 349, 287, 6434, 771, 696, 289, 5168, 5314, 268, 2341, 292, 349, 10052, 289, 472, 9165, 1416, 391, 2493, 552, 391, 6224, 635, 12104, 315, 391, 827, 836, 387, 268, 6626, 840, 747, 315, 391, 4598, 46, 315, 7807, 289, 419, 25458, 292, 315, 391, 837, 2667, 315, 839, 289, 743, 3821, 3072, 336, 315, 8876, 621, 292, 341, 1840, 289, 807, 490, 349, 19123, 289, 268, 25525, 771, 391, 293, 268, 10898, 58, 10528, 1557, 2108, 319, 622, 289, 426, 336, 1580, 9483, 52, 1848, 315, 3917, 3390, 1605, 391, 363, 6368, 2086, 34, 659, 11981, 2798, 2150, 622, 13931, 4417, 697, 549, 16760, 13043, 391, 7668, 11376, 671, 315, 391, 944, 6809, 3959, 1860, 349, 9674, 350, 549, 14697, 349, 1688, 289, 268, 4831, 866, 349, 4557, 1804, 457, 30870, 1990, 391, 9068, 350, 262, 4123, 294, 9360, 292, 315, 391, 10130, 738, 289, 268, 25525, 20224, 314, 349, 3234, 2714, 328, 549, 6233, 292, 391, 5496, 46, 771, 1896, 549, 2722, 900, 292, 10137, 807, 12714, 21974, 387, 268, 2734, 326, 549, 8790, 336, 349, 622, 17680, 46, 659, 391, 262, 8280, 294, 29781, 1018, 293, 549, 8963, 365, 2484, 910, 365, 341, 20595, 6224, 17818, 8143, 1765, 518, 274, 6141, 1744, 549, 2845, 110, 636, 4270, 1258, 262, 21921, 315, 3925, 900, 292, 3202, 289, 740, 1279, 315, 642, 541, 3959, 315]
# print(t.decode(d))
# print(t.visualize((list(range(32768)))))
#
#
# with open("data/combined_sample.txt", encoding="utf-8") as f:
# 	t.corpus = f.read()
# t.build(2048)
# t.save("tok2048")
# t.build(32768, checkpoints = [8192, 16384])
# t.save("newtokens32768")
# # starting 12:37
# print(time.ctime())
# 1:11

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
# t.corpus = "hello<|nameStart|>john<|nameEnd|><|msgStart|>world frfr testing aha im gonna kms woah who said that why did u say that the lion and the witch and the wardrobe foo bar antimony arsenic aluminum selenium hydrogen oxygen nitrogen rhenium nickel neodymium neptunium germanium iron americium ruthenium uranium europium zirconium lutetium vanadium lanthanum<|msgEnd|>"


# with open("swift.txt", encoding="utf-8") as f:
	# t.corpus = f.read()

# t.load("tokens32768")


# t.encode(t.corpus[:100])

# t.build(500)
# print(t.fromBytes(t.decode(t.encode(t.corpus[:1000]))))
# t.save("debug")
# print(t.visualize())
# print(t.corpus)
# # print(t.fromBytes(t.decode(t.encode(t.corpus))))
# print(t.visualize(t.encode(t.corpus)))