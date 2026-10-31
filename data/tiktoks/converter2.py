import json



name = "converted32768"

limit = 400

with open(f"{name}.json", "r", encoding="utf-8") as f:
	data = json.load(f)
	merges = {int(k): v for k, v in data["merges"].items()}

out = []
l = 0
for m in merges:
	out.append(f'{{{m}, {merges[m]}}}')
	l += 1
	if l == limit:
		break
print("".join(["{", ", ".join(out), "};"]))