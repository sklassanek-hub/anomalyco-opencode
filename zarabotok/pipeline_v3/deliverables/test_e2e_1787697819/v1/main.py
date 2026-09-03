import json
def solve(data):
    return {"result": sorted(data)}

if __name__ == "__main__":
    print(json.dumps(solve([3,1,2])))
