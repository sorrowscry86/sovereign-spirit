import time
import os
import json
from src.core.memory.stasis_chamber import StasisChamber

def test_stasis_benchmark():
    os.makedirs("stasis_tanks", exist_ok=True)
    tank_path = os.path.abspath("stasis_tanks/poisoned_apple.json")
    ptr_path = os.path.abspath("stasis_tanks/poisoned_apple.ptr")
    
    # Generate 50MB-ish JSON
    data = {f"key_{i}": "A" * 1000 for i in range(50000)}
    with open(tank_path, "w") as f:
        json.dump(data, f)
    
    with open(ptr_path, "w") as f:
        f.write(tank_path)
        
    chamber = StasisChamber()
    
    start = time.time()
    thawed_data = chamber.thaw(ptr_path)
    end = time.time()
    
    duration = end - start
    print(f"\n[BENCHMARK] Thawed {len(thawed_data)} keys in {duration:.4f} seconds")
    
    assert len(thawed_data) == 50000
    assert duration < 2.0  # Threshold for "Poisoned Apple"

if __name__ == "__main__":
    test_stasis_benchmark()
