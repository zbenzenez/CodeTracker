import requests
import sys
import json
from datetime import datetime

class CodeTrackerAPITester:
    def __init__(self, base_url="https://devtask-reminder.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.username = "NK-NiteshKumar"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=30):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)

            print(f"   Status: {response.status_code}")
            
            success = response.status_code == expected_status
            
            if success:
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")
                    self.log_test(name, True)
                    return True, response_data
                except:
                    print(f"   Response: {response.text[:200]}...")
                    self.log_test(name, True)
                    return True, {}
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data}"
                except:
                    error_msg += f" - {response.text[:100]}"
                
                self.log_test(name, False, error_msg)
                return False, {}

        except requests.exceptions.Timeout:
            error_msg = f"Request timeout after {timeout}s"
            self.log_test(name, False, error_msg)
            return False, {}
        except Exception as e:
            error_msg = f"Request error: {str(e)}"
            self.log_test(name, False, error_msg)
            return False, {}

    def test_health_endpoint(self):
        """Test health check endpoint"""
        return self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )

    def test_github_check(self):
        """Test GitHub commit check"""
        return self.run_test(
            "GitHub Commit Check",
            "GET",
            f"github/check/{self.username}",
            200,
            timeout=45  # GitHub API might be slower
        )

    def test_leetcode_check(self):
        """Test LeetCode POTD check"""
        return self.run_test(
            "LeetCode POTD Check",
            "GET",
            f"leetcode/check/{self.username}",
            200,
            timeout=45  # Web scraping might be slower
        )

    def test_dashboard(self):
        """Test dashboard endpoint"""
        return self.run_test(
            "Dashboard Data",
            "GET",
            f"dashboard/{self.username}",
            200,
            timeout=60  # Combined data might take longer
        )

    def test_create_trigger(self):
        """Test creating a notification trigger"""
        trigger_data = {
            "platform": "github",
            "username": self.username,
            "trigger_time": "23:45",
            "enabled": True
        }
        
        success, response = self.run_test(
            "Create Trigger",
            "POST",
            "triggers",
            200,  # Expecting 200, but backend might return 201
            data=trigger_data
        )
        
        if not success:
            # Try with 201 status code
            success, response = self.run_test(
                "Create Trigger (201)",
                "POST",
                "triggers",
                201,
                data=trigger_data
            )
        
        return success, response

    def test_get_triggers(self):
        """Test getting user triggers"""
        return self.run_test(
            "Get User Triggers",
            "GET",
            f"triggers/{self.username}",
            200
        )

    def test_delete_trigger(self, trigger_id):
        """Test deleting a trigger"""
        if not trigger_id:
            self.log_test("Delete Trigger", False, "No trigger ID provided")
            return False, {}
            
        return self.run_test(
            "Delete Trigger",
            "DELETE",
            f"triggers/{trigger_id}",
            200
        )

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Code Tracker API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print(f"👤 Username: {self.username}")
        print("=" * 60)

        # Test 1: Health Check
        health_success, health_data = self.test_health_endpoint()
        
        # Test 2: GitHub Integration
        github_success, github_data = self.test_github_check()
        
        # Test 3: LeetCode Integration  
        leetcode_success, leetcode_data = self.test_leetcode_check()
        
        # Test 4: Dashboard
        dashboard_success, dashboard_data = self.test_dashboard()
        
        # Test 5: Create Trigger
        trigger_success, trigger_data = self.test_create_trigger()
        trigger_id = trigger_data.get('id') if trigger_success else None
        
        # Test 6: Get Triggers
        get_triggers_success, triggers_data = self.test_get_triggers()
        
        # Test 7: Delete Trigger (if we created one)
        delete_success = False
        if trigger_id:
            delete_success, _ = self.test_delete_trigger(trigger_id)
        else:
            self.log_test("Delete Trigger", False, "No trigger to delete")

        # Print Summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"  {status} - {result['name']}")
            if not result["success"] and result["details"]:
                print(f"    └─ {result['details']}")

        # Critical Issues Check
        critical_failures = []
        if not health_success:
            critical_failures.append("Health endpoint not responding")
        if not github_success:
            critical_failures.append("GitHub integration not working")
        if not leetcode_success:
            critical_failures.append("LeetCode integration not working")
        if not dashboard_success:
            critical_failures.append("Dashboard endpoint not working")

        if critical_failures:
            print(f"\n🚨 CRITICAL ISSUES FOUND:")
            for issue in critical_failures:
                print(f"  • {issue}")
            return 1
        
        print(f"\n🎉 Backend API testing completed!")
        return 0 if self.tests_passed == self.tests_run else 1

def main():
    tester = CodeTrackerAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())