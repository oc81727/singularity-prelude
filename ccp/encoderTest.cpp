#include <iostream>
#include <unordered_map>
#include <queue>
#include <unordered_set>
#include <string>
#include <vector>
#include <deque>
#include <map>
#include <cstdint>
#include <stdexcept>
#include "include/nlohmann/json.hpp"
#include <fstream>
#include <numeric>

#include <ctime>
using namespace std;
using json = nlohmann::json;



class Tokenizer {
    public:
    vector<string> special = {"<|nameStart|>", "<|nameEnd|>", "<|msgStart|>", "<|msgEnd|>", "<|endOfDocument|>"};
    unordered_map<string, uint16_t> specialToToken = {{"<|nameStart|>", 256}, {"<|nameEnd|>", 257}, {"<|msgStart|>", 258}, {"<|msgEnd|>", 259}, {"<|endOfDocument|>", 260}};
    unordered_map<uint16_t, uint16_t> specialLength = {{256, 13}, {257, 11}, {258, 12}, {259, 10}, {260, 17}};
    string corpus = "frfr<|nameStart|>jesus<|nameEnd|><|msgStart|>hello world<|msgEnd|><|endOfDocument|>frfr";
    unordered_map<uint32_t, uint16_t> merges;
    // encoded pair: value
    
    unordered_map<uint32_t, int> versions;
    unordered_map<uint32_t, int> pairLengths;
    vector<uint16_t> byteArray;
    vector<int> nextIndex;
    vector<int> prevIndex;
    vector<int> pairIndex;

    priority_queue<pair<uint16_t, pair<int, uint32_t>>, vector<pair<uint16_t, pair<int, uint32_t>>>, greater<pair<uint16_t, pair<int, uint32_t>>>> heap;
    // min heap


    uint32_t encodePair(uint16_t v1, uint16_t v2) {
        return (static_cast<uint32_t>(v1) << 16) | v2;
    }

    void decodePair(int e, int& v1, int& v2) {
        v1 = e >> 16;
        v2 = e & 0xFFFF;
    }

    string loadString(string filepath) {
        ifstream file(filepath);
        string content((istreambuf_iterator<char>(file)), istreambuf_iterator<char>());
        return content;
    }

    void load(string filepath) {
        ifstream file(filepath);
        json j;
        file >> j;

        merges = unordered_map<uint32_t, uint16_t>();

        for (const auto& [key, value] : j.at("merges").items())
        {
            uint32_t k = stoul(key);
            uint16_t v = value.get<uint16_t>();

            merges[k] = v;
        }
    }

    vector<uint16_t> toBytes(const string& str) {
        map<size_t, uint16_t> occPos; // {position, val}
        for (auto& pair : specialToToken) {
            string target = pair.first;
            uint16_t id = pair.second;
            size_t pos = str.find(target);
            while (pos != string::npos) {
                occPos[pos] = id;
                pos = str.find(target, pos + 1);
            }
        }

        vector<uint16_t> bytes;
        size_t currentPos = 0;
        for (auto& pair : occPos) {
            size_t pos = pair.first;
            uint16_t val = pair.second;
            // bytes.insert(bytes.end(), str.begin() + currentPos, str.begin() + pos);
            for (size_t i = currentPos; i < pos; i++) {
                bytes.push_back(static_cast<unsigned char>(str[i]));
            }
            bytes.push_back(val);
            currentPos += (pos - currentPos) + specialLength.at(val);
        }
        for (size_t i = currentPos; i < str.size(); i++) {
            bytes.push_back(static_cast<unsigned char>(str[i]));
        }
        // bytes.insert(bytes.end(), str.begin() + currentPos, str.end());
        
        return bytes;
    }


    void saveBin(const vector<uint16_t>& data, const string& filename) {
        ofstream file(filename, ios::binary);

        if (!file) {
            throw runtime_error("Could not open file");
        }

        file.write(
            reinterpret_cast<const char*>(data.data()),
            data.size() * sizeof(uint16_t)
        );

        if (!file) {
            throw runtime_error("Write failed");
        }
    }


    void printVec(auto& vec) {
        for (auto v : vec) {
            cout << v << " ";
        }
        cout << endl;
    }

    void printMap(auto& map) {
        for (auto [k, v] : map) {
            cout << k << ": " << v << ", ";
        }
        cout << endl;
    }

    void printVecMap(auto& map) {
        for (auto [k, v] : map) {
            cout << k << ": ";
            for (auto i : v) {
                cout << i << " ";
            }
            cout << endl;
        }
        cout << endl;
    }


    void addPair(unordered_map<uint32_t, vector<int>>& pairs, uint16_t v1, uint16_t v2, int n, vector<int>& pairIndex) {
        uint32_t enc = encodePair(v1, v2);
        if (pairs.find(enc) == pairs.end()) { // not in pairs
            pairs[enc] = vector<int>();
            versions[enc] = 0;
            pairLengths[enc] = 1;
        } else {
            versions[enc] += 1;
            pairLengths[enc] += 1;
        }
        pairIndex[n] = pairs[enc].size();
        pairs[enc].push_back(n);

    }

    unordered_map<uint32_t, vector<int>> getPairs() {
        unordered_map<uint32_t, vector<int>> pairs;
        for (size_t i = 0; i < byteArray.size() - 1; i++) {
            addPair(pairs, byteArray[i], byteArray[i+1], i, pairIndex);
        }
        return pairs;
    }

    void addHeap(uint32_t pairEnc, priority_queue<pair<uint16_t, pair<int, uint32_t>>, vector<pair<uint16_t, pair<int, uint32_t>>>, greater<pair<uint16_t, pair<int, uint32_t>>>>& toHeap) {
        if (merges.find(pairEnc) == merges.end()) {
            return;
        }
        uint16_t m = merges[pairEnc];
        int v = versions[pairEnc];
        pair<uint16_t, pair<int, int>> heapVal = make_pair(m, make_pair(v, pairEnc));
        toHeap.push(heapVal);
    }

    void reheap(unordered_map<uint32_t, vector<int>>& pairs) {
        priority_queue<pair<uint16_t, pair<int, uint32_t>>, vector<pair<uint16_t, pair<int, uint32_t>>>, greater<pair<uint16_t, pair<int, uint32_t>>>> newHeap;

        for (auto& [k, v] : pairs) {
            if (pairLengths[k] > 0) {
                addHeap(k, newHeap);
            }
        }
        heap = move(newHeap);
    }


    vector<uint16_t> encode(string& text) {
        uint16_t token;
        int ver;
        uint32_t currentEnc;
        int pre;
        int post;
        int postPost;

        heap = priority_queue<pair<uint16_t, pair<int, uint32_t>>, vector<pair<uint16_t, pair<int, uint32_t>>>, greater<pair<uint16_t, pair<int, uint32_t>>>>();

        versions = unordered_map<uint32_t, int>();
        // unordered_map<uint16_t, int> versions;
        pairLengths = unordered_map<uint32_t, int>();
        // unordered_map<int, int> pairLengths;
        byteArray = toBytes(text);
        size_t byteLength = byteArray.size();
        cout << "num bytes: " << byteLength << endl;

        nextIndex = vector<int>(byteLength);
        iota(nextIndex.begin(), nextIndex.end(), 1);
        nextIndex[byteLength - 1] = -1;

        prevIndex = vector<int>(byteLength);
        iota(prevIndex.begin(), prevIndex.end(), -1);

        pairIndex = vector<int>(byteLength);


        unordered_map<uint32_t, vector<int>> pairs = getPairs();

        for (auto& [k, v] : pairs) {
            addHeap(k, heap);
        }
        // cout << "finished init" << endl;

        while (true) {
            // if (heap.size() > 40000 * pairs.size()) {
            //     reheap(pairs);
            // }
            bool b = false;
            while (true) {
                if (heap.size() == 0) {
                    b = true;
                    break;
                }
                pair<uint16_t, pair<int, uint32_t>> heapTop = heap.top();
                heap.pop();
                token = heapTop.first;
                ver = heapTop.second.first;
                currentEnc = heapTop.second.second;
                if (versions[currentEnc] != ver) {
                    continue;
                }
                break;
            }
            if (b) {
                // cout << "finished" << endl;
                break;
            }
            // cout << "current enc: " << currentEnc << endl; 

            vector<int>& toProcess = pairs[currentEnc];
            for (int curr : toProcess) {
                if (curr == -1) {continue;}
                pre = prevIndex[curr];
                post = nextIndex[curr];
                if (post != -1) {
                    postPost = nextIndex[post];
                } else {
                    postPost = -1;
                }

                if (pre != -1) {
                    uint32_t enc = encodePair(byteArray[pre], byteArray[curr]);
                    pairs[enc][pairIndex[pre]] = -1;
                    if (enc != currentEnc) {
                        versions[enc] += 1;
                        addHeap(enc, heap);
                    }
                    pairLengths[enc] -= 1;
                }
                if (postPost != -1) {
                    uint32_t enc = encodePair(byteArray[post], byteArray[postPost]);
                    pairs[enc][pairIndex[post]] = -1;
                    if (enc != currentEnc) {
                        versions[enc] += 1;
                        addHeap(enc, heap);
                    }
                    pairLengths[enc] -= 1;
                }

                byteArray[post] = -1;
                int prev = prevIndex[post];
                int nex = nextIndex[post];
                if (prev != -1) {
                    nextIndex[prev] = nex;
                }
                if (nex != -1) {
                    prevIndex[nex] = prev;
                }
                nextIndex[post] = -1;
                prevIndex[post] = -1;
                byteArray[curr] = token;

                if (pre != -1) {
                    uint32_t enc = encodePair(byteArray[pre], byteArray[curr]);
                    addPair(pairs, byteArray[pre], byteArray[curr], pre, pairIndex);
                    addHeap(enc, heap);
                }
                post = nextIndex[curr];
                if (post != -1) {
                    uint32_t enc = encodePair(byteArray[curr], byteArray[post]);
                    addPair(pairs, byteArray[curr], byteArray[post], curr, pairIndex);
                    addHeap(enc, heap);
                }


            }

        }
        int index = 0;
        vector<uint16_t> t = {byteArray[0]};
        while (nextIndex[index] != -1) {
            index = nextIndex[index];
            t.push_back(byteArray[index]);
        }

        return t;




    }


};


int main() {
    
    Tokenizer t = Tokenizer();
    t.load("../data/tiktoks/converted8192.json");
    string text = t.loadString("../data/fine/txt/frog_clean.txt");
    t.saveBin(t.encode(text), "../data/fine/bin/1.bin");

    text = t.loadString("../data/fine/txt/mad_clean.txt");
    t.saveBin(t.encode(text), "../data/fine/bin/2.bin");

    text = t.loadString("../data/fine/txt/war_clean.txt");
    t.saveBin(t.encode(text), "../data/fine/bin/3.bin");
    // t.printMap(t.merges);
    // cout << t.corpus << endl;
    // vector<uint16_t> encoded = t.encode(t.corpus);
    // t.printVec(encoded);
    // for (int i = 1; i <= 100; i++) {
    //     string text = t.loadString("../data/paraqeet/iliketrains/txt/" + to_string(i) + ".txt");
    //     std::time_t now = std::time(nullptr);
    //     std::cout << std::ctime(&now);
    //     cout << "starting " << i << endl;
    //     vector<uint16_t> encoded = t.encode(text);
    //     cout << "saving" << endl;
    //     t.saveBin(encoded, "../data/paraqeet/iliketrains/bin/" + to_string(i) + ".bin");
    //     cout << "done!" << endl;
    // }

    return 0;
}