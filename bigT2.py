import heapq, json, re, time


class LinkedList():
	def __init__(self):
		self.start = None
		self.end = None
		self.length = 0

	def append(self, value):
		node = LinkedNode(value, self)
		if self.length == 0:
			self.start = node
			self.end = node
		else:
			self.end.next = node
			node.prev = self.end
			self.end = node

		self.length += 1

	def insert(self, node, value):
		n = LinkedNode(value, self)
		if node.next is None: # at end
			node.next = n
			n.prev = node
			self.end = n
		else:
			a = node.next
			node.next = n
			a.prev = n
			n.prev = node
			n.next = a

		self.length += 1

	def appendNode(self, node):
		node.parent = self
		if self.length == 0:
			self.start = node
			self.end = node
		else:
			self.end.next = node
			self.end = node
		self.length += 1

	def removeNode(self, node):
		if node.parent is not self:
			raise Exception(f"removing node {node} from a foreign list {self}")
		if self.length == 1:
			self.start = None
			self.end = None
		elif self.end is node:
			self.end = node.prev
			self.end.next = None
		elif self.start is node:
			self.start = node.next
			self.start.prev = None
		else:
			node.prev.next = node.next
			node.next.prev = node.prev
		self.length -= 1
		node.unlink()

	def toList(self):
		if self.length == 0:
			return []
		curr = self.start
		l = []
		while True:
			l.append(curr.value)
			if curr.next is not None:
				curr = curr.next
			else:
				return l

	def setList(self, l):
		for i in l:
			self.append(i)

	def loop(self):
		if self.length == 0:
			return
		curr = self.start
		yield curr
		while curr.next is not None:
			curr = curr.next
			yield curr

	def __repr__(self):
		return f"<LinkedList({self.toList()})>"


class LinkedNode():
	def __init__(self, value, parent = None):
		self.value = value
		self.active = True
		self.prev = None
		self.next = None
		self.parent = parent

	def unlink(self):
		self.active = False
		self.prev = None
		self.next = None
		self.parent = None

	def __str__(self):
		return f"<Node({self.value})>"

	def __repr__(self):
		return f"<Node({self.value})>"






class Tokenizer():
	def __init__(self):
		self.corpus = ""
		self.bytes = []
		self.merges = {}
		self.mergesInv = {}
		self.safeDistance = 1000000
		self.special = ["<|nameStart|>", "<|nameEnd|>", "<|msgStart|>", "<|msgEnd|>"]
		self.customSplit = "|".join([i.replace("|", "\\|") for i in self.special])
		self.customReplace = {self.special[n]: 256+n for n in range(len(self.special))} # token to id
		self.customReplaceInv = {v:k for k,v in self.customReplace.items()} # id to token
		self.vocabSize = 256 + len(self.special)
		self.bannedStart = list(range(256, 256 + len(self.special))) + [ord(i) for i in ["\n"]]
		self.bannedEnd = list(range(256, 256 + len(self.special))) + [ord(i) for i in [" ", "\n"]]
		self.heap = []
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
		print(textBytes)
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
		for i in range(num):
			# print(textBytes)
			if checkpoints is not None and i in checkpoints:
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
			print(f"{newToken} {commonPair}")
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






		



t = Tokenizer()


# with open("data/combined_sample.txt", encoding="utf-8") as f:
# 	t.corpus = f.read()
# t.build(32768-256, checkpoints = [8192-256, 16384-256])
# t.save("newtokens32768")
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


with open("swift.txt", encoding="utf-8") as f:
	t.corpus = f.read()

# t.load("tokens32768")


# t.encode(t.corpus[:100])

t.build(10000)
t.save("debug")
# print(t.visualize())
# print(t.corpus)
# # print(t.fromBytes(t.decode(t.encode(t.corpus))))
print(t.visualize(t.encode(t.corpus)))