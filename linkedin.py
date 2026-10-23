

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
			node.prev = self.end # forgot this line! good thing this function is useless
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
