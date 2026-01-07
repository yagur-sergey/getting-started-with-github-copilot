"""
Test suite for the Mergington High School Activities API.

Tests cover all API endpoints including:
- GET /activities - retrieve all activities
- POST /activities/{activity_name}/signup - sign up for an activity
- DELETE /activities/{activity_name}/unregister - unregister from an activity
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test."""
    # Save original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint."""
    
    def test_get_activities_success(self, client):
        """Test that we can retrieve all activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Check that we got a dictionary of activities
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check that each activity has the required fields
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)
    
    def test_get_activities_contains_expected_activities(self, client):
        """Test that specific activities are present."""
        response = client.get("/activities")
        data = response.json()
        
        # Check for some expected activities
        assert "Soccer Team" in data
        assert "Drama Club" in data
        assert "Programming Class" in data


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint."""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity."""
        email = "newstudent@mergington.edu"
        activity_name = "Soccer Team"
        
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity_name in data["message"]
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
    
    def test_signup_duplicate_participant(self, client):
        """Test that signing up twice for the same activity fails."""
        email = "duplicate@mergington.edu"
        activity_name = "Basketball Team"
        
        # First signup should succeed
        response1 = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"].lower()
    
    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity."""
        email = "student@mergington.edu"
        activity_name = "Nonexistent Activity"
        
        response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_signup_with_special_characters(self, client):
        """Test signup with email containing special characters."""
        from urllib.parse import quote
        email = "test+student@mergington.edu"
        activity_name = "Chess Club"
        
        response = client.post(
            f"/activities/{quote(activity_name)}/signup?email={quote(email)}"
        )
        
        assert response.status_code == 200
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint."""
    
    def test_unregister_success(self, client):
        """Test successful unregistration from an activity."""
        email = "test@mergington.edu"
        activity_name = "Drama Club"
        
        # First sign up
        client.post(f"/activities/{activity_name}/signup?email={email}")
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity_name]["participants"]
        
        # Now unregister
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant."""
        activity_name = "Soccer Team"
        # Get an existing participant
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        email = activities_data[activity_name]["participants"][0]
        
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        assert response.status_code == 200
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity_name]["participants"]
    
    def test_unregister_not_registered(self, client):
        """Test unregistering a participant who is not registered."""
        email = "notregistered@mergington.edu"
        activity_name = "Science Club"
        
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"].lower()
    
    def test_unregister_activity_not_found(self, client):
        """Test unregister from non-existent activity."""
        email = "student@mergington.edu"
        activity_name = "Nonexistent Activity"
        
        response = client.delete(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestRootEndpoint:
    """Tests for GET / endpoint."""
    
    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static HTML."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestEndToEndWorkflow:
    """Integration tests for complete user workflows."""
    
    def test_complete_signup_and_unregister_workflow(self, client):
        """Test a complete workflow: check activities, signup, unregister."""
        email = "workflow@mergington.edu"
        activity_name = "Art Studio"
        
        # 1. Get activities and check initial state
        response = client.get("/activities")
        initial_data = response.json()
        initial_count = len(initial_data[activity_name]["participants"])
        
        # 2. Sign up for activity
        signup_response = client.post(
            f"/activities/{activity_name}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # 3. Verify participant count increased
        response = client.get("/activities")
        after_signup_data = response.json()
        after_signup_count = len(after_signup_data[activity_name]["participants"])
        assert after_signup_count == initial_count + 1
        assert email in after_signup_data[activity_name]["participants"]
        
        # 4. Unregister from activity
        unregister_response = client.delete(
            f"/activities/{activity_name}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # 5. Verify participant count decreased
        response = client.get("/activities")
        final_data = response.json()
        final_count = len(final_data[activity_name]["participants"])
        assert final_count == initial_count
        assert email not in final_data[activity_name]["participants"]
    
    def test_multiple_signups_different_activities(self, client):
        """Test signing up for multiple different activities."""
        email = "multisport@mergington.edu"
        activities_to_join = ["Soccer Team", "Basketball Team", "Gym Class"]
        
        for activity_name in activities_to_join:
            response = client.post(
                f"/activities/{activity_name}/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify participant is in all activities
        response = client.get("/activities")
        data = response.json()
        for activity_name in activities_to_join:
            assert email in data[activity_name]["participants"]
