with open("combined_clean2.txt",encoding="utf-8") as f:
	a = f.read()
with open("sample.txt",encoding="utf-8") as f:
	b = f.read()
with open("combined_sample.txt", "a",encoding="utf-8") as f:
	f.write(a)
	f.write("\n")
	f.write(b)