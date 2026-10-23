
# split by spaces and any defined special characters
# for any word, record metadata about:
# length/existence of spaces before
# encode capitalization (rotational maybe?) nah i hate spinning
# for numbers, replace with single number token
# for long numbers, split into chunks of defined lengths
# add value encoding information
# for long numbers, also encode information about position of current segment, or may not be necessary bc of kqv?
# little endian or big endian? prob big, make it configurable



from linkedin import LinkedList, LinkedNode
import re, heapq


# class Char():
# 	def __init__(self, c):
# 		self.original = c
# 		self.value = c.lower()
# 		self.isCap = self.original != self.value

# 	def __str__(self):
# 		return f"'{self.original}'"

# 	def __repr__(self):
# 		return f"'{self.original}'"


class Token():
	def __init__(self, c):
		self.value = c
		# self.isFullCap = c.upper() == c
		# self.isFirstCap = self.isFullCap # 1 character only in init
		# self.isOtherCap = False
		# self.code = ord(c) if code is None else code
		self.pairPointer = None

	def __str__(self):
		return f"'{self.value}'"

	def __repr__(self):
		return f"'{self.value}'"



class Tokenizer():
	def __init__(self):
		self.corpus = "Hello🍉 WORLD!  I HATE myself and maybe should end it all, in Minecraft aha"
		self.specialTokens = ["<|nameStart|>", "<|msgStart|>", "<|number|>", "<|endOfDocument|>"]
		self.specialSplits = [33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 58, 59, 60, 61, 62, 63, 64, 123, 124, 125, 126]
		# ascii between 33 and 47 inclusive, 58 and 64 inclusive, 91 and 96 inclusive, 123 and 126 inclusive
		self.specialSplitRegex = "|".join(["\\" + chr(i) for i in self.specialSplits])
		self.safeDistance = 10000000


	def encodePair(self, v1, v2):
		return v1 * self.safeDistance + v2

	def decodePair(self, enc):
		v1 = enc // self.safeDistance
		v2 = enc % self.safeDistance
		return v1, v2

	def toBytes(self, text):
		return text.encode("utf-8")

	def getPairs(self, pairs, l):
		curr = l.start
		if l.length == 1:
			return
		for i in range(l.length - 1):
			# print(curr, curr.next)
			# input()
			enc = self.encodePair(curr.value.value, curr.next.value.value)
			if enc not in pairs:
				pairs[enc] = LinkedList()
			pairs[enc].append(curr)
			pairs[enc].end.pairPointer = curr

			curr = curr.next




	def build(self, size):
		heap = []
		words = [self.toBytes(i) for i in self.corpus.split(" ")]
		wordsLinked = [LinkedList([Token(c) for c in list(w)]) for w in words]
		# print(wordsLinked)
		pairs = {}
		for word in wordsLinked:
			self.getPairs(pairs, word)
		versions = {enc: 0 for enc in pairs}
		for p in pairs:
			heapq.heappush(heap, (-pairs[p].length, versions[p], p))

		for i in wordsLinked[0].loop():
			print(i)

		for i in range(size):
			curr = heapq.heappop(heap)
			while curr[1] != versions[curr[2]]:
				curr = heapq.heappop(heap)

			# remove occurences in pairs
			currEnc = p


			# if curr.prev != None: 
			# 	curr.prev.pairPointer.parent.remove(curr.prev.pairPointer)
			# # update heap versions
			# 	enc = self.encodePair(curr.prev.value.code, curr.value.code)
			# merge
			# add new occurences to pairs
			# update heap versions


		pass


t = Tokenizer()
# print(t.specialSplits)
# print(t.specialSplitRegex)
t.build(5)