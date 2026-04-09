#!/usr/bin/env python3
"""
Comprehensive backend API testing for Milk Collection Management System
Tests all CRUD operations, authentication, and reports functionality
"""

import requests
import json
import sys
from datetime import datetime, timedelta

# Configuration
BASE_URL = "https://milk-tracker-66.preview.emergentagent.com/api"
ADMIN_EMAIL = "admin@milktracker.com"
ADMIN_PASSWORD = "admin123"

class MilkTrackerAPITester:
    def __init__(self):
        self.base_url = BASE_URL
        self.session = requests.Session()
        self.access_token = None
        self.producer_id = None
        self.collector_id = None
        self.collection_id = None
        self.test_results = []
        
    def log_test(self, test_name, success, message="", response_data=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            "test": test_name,
            "success": success,
            "message": message,
            "response_data": response_data
        })
        
    def make_request(self, method, endpoint, data=None, params=None, use_auth=True):
        """Make HTTP request with optional authentication"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}
        
        if use_auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
            
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, params=params, timeout=30)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            return response
        except requests.exceptions.Timeout:
            print(f"Request timeout for {method} {url}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"Connection error for {method} {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed for {method} {url}: {e}")
            return None
    
    def test_authentication(self):
        """Test authentication endpoints"""
        print("\n=== AUTHENTICATION TESTING ===")
        
        # Test login
        login_data = {
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
        
        response = self.make_request("POST", "/auth/login", data=login_data, use_auth=False)
        
        if response and response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                self.access_token = data["access_token"]
                user_info = data["user"]
                self.log_test(
                    "Admin Login", 
                    True, 
                    f"Successfully logged in as {user_info.get('name', 'Unknown')} ({user_info.get('role', 'Unknown')})",
                    data
                )
            else:
                self.log_test("Admin Login", False, "Missing access_token or user in response", data)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("Admin Login", False, error_msg)
            return False
            
        # Test get current user info
        response = self.make_request("GET", "/auth/me")
        
        if response and response.status_code == 200:
            data = response.json()
            self.log_test(
                "Get User Info", 
                True, 
                f"Retrieved user info for {data.get('name', 'Unknown')} (Role: {data.get('role', 'Unknown')})",
                data
            )
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("Get User Info", False, error_msg)
            
        return True
    
    def test_producer_management(self):
        """Test producer CRUD operations"""
        print("\n=== PRODUCER MANAGEMENT TESTING ===")
        
        # Create producer
        producer_data = {
            "name": "João Silva",
            "nickname": "Joca",
            "email": "joao@test.com",
            "phone": "11999999999",
            "address": "Fazenda São João, Zona Rural"
        }
        
        response = self.make_request("POST", "/producers", data=producer_data)
        
        if response and response.status_code == 200:
            data = response.json()
            if "id" in data:
                self.producer_id = data["id"]
                self.log_test(
                    "Create Producer", 
                    True, 
                    f"Created producer '{data.get('name')}' with ID: {self.producer_id}",
                    data
                )
            else:
                self.log_test("Create Producer", False, "Missing ID in response", data)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("Create Producer", False, error_msg)
            
        # List producers
        response = self.make_request("GET", "/producers")
        
        if response and response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                producer_count = len(data)
                self.log_test(
                    "List Producers", 
                    True, 
                    f"Retrieved {producer_count} producer(s)",
                    {"count": producer_count, "producers": data[:2]}  # Show first 2 for brevity
                )
                
                # Save first producer ID if we don't have one
                if not self.producer_id and data:
                    self.producer_id = data[0].get("id")
                    
            else:
                self.log_test("List Producers", False, "Response is not a list", data)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("List Producers", False, error_msg)
    
    def test_collector_management(self):
        """Test collector CRUD operations"""
        print("\n=== COLLECTOR MANAGEMENT TESTING ===")
        
        # Create collector
        collector_data = {
            "name": "Maria Santos",
            "phone": "11988888888",
            "email": "maria@test.com"
        }
        
        response = self.make_request("POST", "/collectors", data=collector_data)
        
        if response and response.status_code == 200:
            data = response.json()
            if "id" in data:
                self.collector_id = data["id"]
                self.log_test(
                    "Create Collector", 
                    True, 
                    f"Created collector '{data.get('name')}' with ID: {self.collector_id}",
                    data
                )
            else:
                self.log_test("Create Collector", False, "Missing ID in response", data)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("Create Collector", False, error_msg)
            
        # List collectors
        response = self.make_request("GET", "/collectors")
        
        if response and response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                collector_count = len(data)
                self.log_test(
                    "List Collectors", 
                    True, 
                    f"Retrieved {collector_count} collector(s)",
                    {"count": collector_count, "collectors": data[:2]}  # Show first 2 for brevity
                )
                
                # Save first collector ID if we don't have one
                if not self.collector_id and data:
                    self.collector_id = data[0].get("id")
                    
            else:
                self.log_test("List Collectors", False, "Response is not a list", data)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("List Collectors", False, error_msg)
    
    def test_collection_recording(self):
        """Test collection CRUD operations"""
        print("\n=== COLLECTION RECORDING TESTING ===")
        
        if not self.producer_id:
            self.log_test("Create Collection", False, "No producer ID available for testing")
            return
            
        # Create collection
        collection_data = {
            "producer_id": self.producer_id,
            "date": "2025-07-15",
            "time": "06:30",
            "quantity": 25.5,
            "day_of_week": "Segunda",
            "notes": "Leite de boa qualidade, sem problemas"
        }
        
        response = self.make_request("POST", "/collections", data=collection_data)
        
        if response and response.status_code == 200:
            data = response.json()
            if "id" in data:
                self.collection_id = data["id"]
                self.log_test(
                    "Create Collection", 
                    True, 
                    f"Created collection with ID: {self.collection_id}, Quantity: {data.get('quantity')}L",
                    data
                )
            else:
                self.log_test("Create Collection", False, "Missing ID in response", data)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("Create Collection", False, error_msg)
            
        # List collections
        response = self.make_request("GET", "/collections")
        
        if response and response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                collection_count = len(data)
                total_quantity = sum(c.get("quantity", 0) for c in data)
                self.log_test(
                    "List Collections", 
                    True, 
                    f"Retrieved {collection_count} collection(s), Total quantity: {total_quantity}L",
                    {"count": collection_count, "total_quantity": total_quantity, "collections": data[:2]}
                )
            else:
                self.log_test("List Collections", False, "Response is not a list", data)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("List Collections", False, error_msg)
    
    def test_delete_collection(self):
        """Test delete collection functionality and permissions"""
        print("\n=== DELETE COLLECTION TESTING ===")
        
        # First, ensure we have a collection to delete
        if not self.collection_id:
            print("⚠️  No collection ID available, creating a test collection first...")
            
            # Create a test collection
            collection_data = {
                "producer_id": self.producer_id if self.producer_id else "test_producer_id",
                "date": "2025-01-15",
                "time": "06:30",
                "quantity": 25.5,
                "day_of_week": "Wednesday",
                "photos": []
            }
            
            response = self.make_request("POST", "/collections", data=collection_data)
            if response and response.status_code == 200:
                data = response.json()
                self.collection_id = data.get("_id")
                self.log_test("Create Test Collection for Delete", True, f"Created collection: {self.collection_id}")
            else:
                self.log_test("Create Test Collection for Delete", False, "Failed to create test collection")
                return
        
        # Test 1: Verify collection exists before deletion
        print("🔍 Verifying collection exists before deletion...")
        response = self.make_request("GET", f"/collections/{self.collection_id}")
        if response and response.status_code == 200:
            collection_data = response.json()
            self.log_test("Verify Collection Exists", True, f"Collection found: {collection_data.get('date')} - {collection_data.get('quantity')}L")
        else:
            self.log_test("Verify Collection Exists", False, f"Collection not found or error: {response.status_code if response else 'No response'}")
            return
        
        # Test 2: Test delete without authentication (should fail)
        print("🔒 Testing delete without authentication...")
        response = self.make_request("DELETE", f"/collections/{self.collection_id}", use_auth=False)
        if response and response.status_code in [401, 403]:
            self.log_test("Delete Without Auth", True, f"Correctly rejected (status: {response.status_code})")
        else:
            status = response.status_code if response else "No response"
            self.log_test("Delete Without Auth", False, f"Should have been rejected but got status: {status}")
        
        # Test 3: Test delete with invalid token (should fail)
        print("🔒 Testing delete with invalid token...")
        old_token = self.access_token
        self.access_token = "invalid_token_12345"
        response = self.make_request("DELETE", f"/collections/{self.collection_id}")
        self.access_token = old_token  # Restore valid token
        
        if response and response.status_code in [401, 403]:
            self.log_test("Delete With Invalid Token", True, f"Correctly rejected (status: {response.status_code})")
        else:
            status = response.status_code if response else "No response"
            self.log_test("Delete With Invalid Token", False, f"Should have been rejected but got status: {status}")
        
        # Test 4: Delete collection with admin token (should succeed)
        print("🗑️  Testing delete with admin token...")
        response = self.make_request("DELETE", f"/collections/{self.collection_id}")
        if response and response.status_code == 200:
            data = response.json()
            message = data.get("message", "No message")
            self.log_test("Delete Collection", True, f"Successfully deleted: {message}")
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("Delete Collection", False, error_msg)
            return
        
        # Test 5: Verify collection was deleted (should return 404)
        print("✅ Verifying collection was deleted...")
        response = self.make_request("GET", f"/collections/{self.collection_id}")
        if response and response.status_code == 404:
            self.log_test("Verify Collection Deleted", True, "Collection correctly returns 404 after deletion")
        elif response and response.status_code == 200:
            self.log_test("Verify Collection Deleted", False, "Collection still exists after deletion - DELETE failed")
        else:
            status = response.status_code if response else "No response"
            self.log_test("Verify Collection Deleted", False, f"Unexpected response when verifying deletion: {status}")
        
        # Test 6: Try to delete the same collection again (should return 404)
        print("🔄 Testing delete of already deleted collection...")
        response = self.make_request("DELETE", f"/collections/{self.collection_id}")
        if response and response.status_code == 404:
            self.log_test("Delete Already Deleted Collection", True, "Correctly returns 404 for non-existent collection")
        else:
            status = response.status_code if response else "No response"
            self.log_test("Delete Already Deleted Collection", False, f"Expected 404 but got: {status}")
        
        # Clear the collection_id since it's been deleted
        self.collection_id = None
    def test_reports(self):
        """Test reports functionality"""
        print("\n=== REPORTS TESTING ===")
        
        # Test summary report
        params = {
            "start_date": "2025-07-01",
            "end_date": "2025-07-31"
        }
        
        response = self.make_request("GET", "/reports/summary", params=params)
        
        if response and response.status_code == 200:
            data = response.json()
            required_fields = ["total_quantity", "total_collections", "by_producer"]
            missing_fields = [field for field in required_fields if field not in data]
            
            if not missing_fields:
                self.log_test(
                    "Reports Summary", 
                    True, 
                    f"Summary report: {data.get('total_collections', 0)} collections, {data.get('total_quantity', 0)}L total",
                    data
                )
            else:
                self.log_test(
                    "Reports Summary", 
                    False, 
                    f"Missing required fields: {missing_fields}",
                    data
                )
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("Reports Summary", False, error_msg)
            
        # Test CSV export
        response = self.make_request("GET", "/reports/export", params=params)
        
        if response and response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            if "csv" in content_type.lower() or "text" in content_type.lower():
                csv_content = response.text
                line_count = len(csv_content.split('\n')) - 1  # Subtract header
                self.log_test(
                    "CSV Export", 
                    True, 
                    f"CSV export successful, {line_count} data lines",
                    {"content_type": content_type, "size": len(csv_content)}
                )
            else:
                self.log_test(
                    "CSV Export", 
                    False, 
                    f"Unexpected content type: {content_type}",
                    {"content_type": content_type}
                )
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("CSV Export", False, error_msg)
    
    def test_offline_sync(self):
        """Test offline sync functionality"""
        print("\n=== OFFLINE SYNC TESTING ===")
        
        if not self.producer_id:
            self.log_test("Offline Sync", False, "No producer ID available for testing")
            return
            
        # Test batch sync
        sync_data = [
            {
                "producer_id": self.producer_id,
                "date": "2025-07-16",
                "time": "07:00",
                "quantity": 30.0,
                "day_of_week": "Terça",
                "offline_id": "offline_001",
                "notes": "Sync test collection 1"
            },
            {
                "producer_id": self.producer_id,
                "date": "2025-07-17",
                "time": "07:15",
                "quantity": 28.5,
                "day_of_week": "Quarta",
                "offline_id": "offline_002",
                "notes": "Sync test collection 2"
            }
        ]
        
        response = self.make_request("POST", "/collections/sync", data=sync_data)
        
        if response and response.status_code == 200:
            data = response.json()
            if "synced" in data and "errors" in data:
                synced_count = len(data.get("synced", []))
                error_count = len(data.get("errors", []))
                self.log_test(
                    "Offline Sync", 
                    True, 
                    f"Synced {synced_count} collections, {error_count} errors",
                    data
                )
            else:
                self.log_test("Offline Sync", False, "Missing synced/errors in response", data)
        else:
            error_msg = f"Status: {response.status_code if response else 'No response'}"
            if response:
                try:
                    error_data = response.json()
                    error_msg += f", Error: {error_data.get('detail', 'Unknown error')}"
                except:
                    error_msg += f", Response: {response.text}"
            self.log_test("Offline Sync", False, error_msg)
    
    def run_all_tests(self):
        """Run all API tests"""
        print("🧪 Starting Milk Tracker Backend API Tests")
        print(f"🌐 Testing against: {self.base_url}")
        print(f"👤 Admin credentials: {ADMIN_EMAIL}")
        
        # Run tests in order
        if not self.test_authentication():
            print("❌ Authentication failed - stopping tests")
            return False
            
        self.test_producer_management()
        self.test_collector_management()
        self.test_collection_recording()
        self.test_delete_collection()
        self.test_reports()
        self.test_offline_sync()
        
        # Summary
        print("\n" + "="*50)
        print("📊 TEST SUMMARY")
        print("="*50)
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        print(f"✅ Passed: {passed}/{total}")
        print(f"❌ Failed: {total - passed}/{total}")
        
        if total - passed > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print(f"\n🎯 Success Rate: {(passed/total)*100:.1f}%")
        
        return passed == total

def main():
    """Main test execution"""
    tester = MilkTrackerAPITester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()