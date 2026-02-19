import pytest
from fastapi.testclient import TestClient
from src.app import app, activities

@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)

@pytest.fixture
def reset_activities():
    """Reset activities to a known state before each test"""
    original_activities = {
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        },
        "Gym Class": {
            "description": "Physical education and sports activities",
            "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
            "max_participants": 30,
            "participants": ["john@mergington.edu", "olivia@mergington.edu"]
        }
    }
    
    activities.clear()
    activities.update(original_activities)
    yield
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    def test_root_redirect(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    def test_get_all_activities(self, client, reset_activities):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data

    def test_get_activities_structure(self, client, reset_activities):
        """Test that activity structure is correct"""
        response = client.get("/activities")
        data = response.json()
        activity = data["Chess Club"]
        
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert activity["max_participants"] == 12
        assert len(activity["participants"]) == 2


class TestSignupEndpoint:
    def test_signup_new_student(self, client, reset_activities):
        """Test signing up a new student for an activity"""
        response = client.post("/activities/Chess Club/signup?email=new_student@mergington.edu")
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        
        # Verify student was added
        activities_data = client.get("/activities").json()
        assert "new_student@mergington.edu" in activities_data["Chess Club"]["participants"]

    def test_signup_duplicate_student(self, client, reset_activities):
        """Test that duplicate signup is rejected"""
        # Try to sign up a student already registered
        response = client.post("/activities/Chess Club/signup?email=michael@mergington.edu")
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signing up for a non-existent activity"""
        response = client.post("/activities/Nonexistent Club/signup?email=test@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_with_spaces_in_activity_name(self, client, reset_activities):
        """Test signup with URL-encoded activity names"""
        response = client.post("/activities/Programming%20Class/signup?email=new_dev@mergington.edu")
        assert response.status_code == 200
        
        # Verify student was added
        activities_data = client.get("/activities").json()
        assert "new_dev@mergington.edu" in activities_data["Programming Class"]["participants"]


class TestUnregisterEndpoint:
    def test_unregister_existing_participant(self, client, reset_activities):
        """Test unregistering an existing participant"""
        response = client.delete("/activities/Chess Club/unregister?email=michael@mergington.edu")
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        
        # Verify student was removed
        activities_data = client.get("/activities").json()
        assert "michael@mergington.edu" not in activities_data["Chess Club"]["participants"]

    def test_unregister_nonexistent_participant(self, client, reset_activities):
        """Test unregistering a student not in the activity"""
        response = client.delete("/activities/Chess Club/unregister?email=notregistered@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert "not registered" in data["detail"]

    def test_unregister_from_nonexistent_activity(self, client, reset_activities):
        """Test unregistering from a non-existent activity"""
        response = client.delete("/activities/Nonexistent Club/unregister?email=test@mergington.edu")
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_with_spaces_in_activity_name(self, client, reset_activities):
        """Test unregister with URL-encoded activity names"""
        # First add a student
        client.post("/activities/Programming%20Class/signup?email=temp@mergington.edu")
        
        # Then remove them
        response = client.delete("/activities/Programming%20Class/unregister?email=temp@mergington.edu")
        assert response.status_code == 200
        
        # Verify student was removed
        activities_data = client.get("/activities").json()
        assert "temp@mergington.edu" not in activities_data["Programming Class"]["participants"]


class TestIntegration:
    def test_signup_and_unregister_flow(self, client, reset_activities):
        """Test complete signup and unregister flow"""
        email = "test_flow@mergington.edu"
        activity = "Gym Class"
        
        # Check initial state
        initial = client.get("/activities").json()
        initial_count = len(initial[activity]["participants"])
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify added
        after_signup = client.get("/activities").json()
        assert len(after_signup[activity]["participants"]) == initial_count + 1
        assert email in after_signup[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify removed
        after_unregister = client.get("/activities").json()
        assert len(after_unregister[activity]["participants"]) == initial_count
        assert email not in after_unregister[activity]["participants"]

    def test_multiple_signups(self, client, reset_activities):
        """Test multiple students signing up for an activity"""
        activity = "Gym Class"
        students = [
            "alice@mergington.edu",
            "bob@mergington.edu",
            "charlie@mergington.edu"
        ]
        
        for student in students:
            response = client.post(f"/activities/{activity}/signup?email={student}")
            assert response.status_code == 200
        
        # Verify all were added
        final = client.get("/activities").json()
        for student in students:
            assert student in final[activity]["participants"]
