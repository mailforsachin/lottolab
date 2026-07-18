import requests
import json
import time

BASE_URL = "https://lottolab.omchat.ovh/api/v1"

strategies = [
    {"id": 1, "name": "Random (Quick Pick)"},
    {"id": 2, "name": "Sobol Sequence"},
    {"id": 3, "name": "Monte Carlo Optimized"},
    {"id": 4, "name": "Genetic Algorithm"},
    {"id": 5, "name": "Hybrid AI"}
]

print("🚀 Testing all strategies...")
print("=" * 60)

results = []

for strategy in strategies:
    print(f"\n📊 Testing {strategy['name']}...")
    
    # Run simulation
    response = requests.post(
        f"{BASE_URL}/simulations/",
        json={"strategy_id": strategy["id"], "num_tickets": 1000}
    )
    
    if response.status_code == 200:
        sim = response.json()
        sim_id = sim["id"]
        print(f"  ✅ Simulation #{sim_id} created, waiting for completion...")
        
        # Wait for completion
        time.sleep(5)
        
        # Get results
        result = requests.get(f"{BASE_URL}/simulations/{sim_id}")
        if result.status_code == 200:
            data = result.json()
            results.append({
                "strategy": strategy["name"],
                "tickets": data["total_tickets"],
                "cost": data["total_cost"],
                "won": data["total_won"],
                "roi": data["roi"],
                "best_win": data["best_win"],
                "status": data["status"]
            })
            print(f"  ✅ ROI: {data['roi']:.2f}%")
            print(f"  ✅ Best Win: ${data['best_win']}")
    else:
        print(f"  ❌ Error: {response.status_code}")

print("\n" + "=" * 60)
print("📊 Strategy Performance Comparison")
print("=" * 60)

# Sort by ROI
results.sort(key=lambda x: x['roi'], reverse=True)

for i, result in enumerate(results, 1):
    print(f"\n{i}. {result['strategy']}")
    print(f"   ROI: {result['roi']:.2f}%")
    print(f"   Best Win: ${result['best_win']}")
    print(f"   Total Won: ${result['won']}")
