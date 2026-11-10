import json



name = "checkpoint7931"
newName = "converted8192"



safeDistance = 1000000
def encodePair1(v1, v2):
	return v1 * safeDistance + v2

def decodePair1(enc):
	v1 = enc // safeDistance
	v2 = enc % safeDistance
	return v1, v2


def encodePair2(v1, v2):
	return v1 << 16 | v2

def decodePair2(enc):
	return enc >> 16, enc & 0xffff

with open(f"{name}.json", "r", encoding="utf-8") as f:
	data = json.load(f)
	merges = {int(k): v for k, v in data["merges"].items()}
	mergesInv = {v: decodePair1(k) for k, v in merges.items()}

	bannedStart = data["bannedStart"]
	bannedEnd = data["bannedEnd"]

with open(f"{newName}.json", "w", encoding="utf-8") as f:
	json.dump({"merges": {encodePair2(*decodePair1(k)): v for k, v in merges.items()}, "bannedStart": sorted(list(bannedStart)),
			   "bannedEnd": sorted(list(bannedEnd))}, f, indent=2)

# print(decodePair2(2097268))