import subprocess
import time
import json
from datetime import datetime

class TrafficRampTester:
    def __init__(self, namespace="synthetic-enterprise"):
        self.namespace = namespace
        self.results = []
    
    def set_weight(self, weight):
        cmd = f"kubectl -n {self.namespace} annotate ingress synthetic-enterprise-ingress nginx.ingress.kubernetes.io/canary-weight='{weight}' --overwrite"
        try:
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            time.sleep(2)
            return True
        except:
            return False
    
    def get_weight(self):
        try:
            result = subprocess.run(
                f"kubectl -n {self.namespace} get ingress synthetic-enterprise-ingress -o jsonpath='{{.metadata.annotations.nginx\\.ingress\\.kubernetes\\.io/canary-weight}}'",
                shell=True, check=True, capture_output=True, text=True
            )
            return int(result.stdout.strip()) if result.stdout else 0
        except:
            return -1
    
    def test_weight(self, target):
        print(f"Testing weight {target}%...")
        if not self.set_weight(target):
            print(f"  ❌ Failed to set weight")
            return False
        
        actual = self.get_weight()
        if actual != target:
            print(f"  ❌ Weight mismatch: expected {target}, got {actual}")
            return False
        
        print(f"  ✅ Weight {target}% verified")
        return True
    
    def run_all(self):
        weights = [0, 5, 25, 50, 100]
        passed = 0
        failed = 0
        
        for w in weights:
            if self.test_weight(w):
                passed += 1
            else:
                failed += 1
            time.sleep(2)
        
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "total": len(weights),
            "passed": passed,
            "failed": failed,
            "success": failed == 0
        }
        
        with open("tests/compliance/traffic-ramp-results.json", "w") as f:
            json.dump(result, f, indent=2)
        
        return failed == 0

if __name__ == "__main__":
    tester = TrafficRampTester()
    success = tester.run_all()
    print(f"\n{'✅ All tests passed' if success else '❌ Some tests failed'}")
    exit(0 if success else 1)
