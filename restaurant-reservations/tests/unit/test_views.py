"""
Unit tests for API views
"""

from datetime import date, time
from rest_framework import status
from unittest.mock import patch

from reservations.models import Reservation
from tests.fixtures.factories import ReservationFactory, ConfirmedReservationFactory
from tests.fixtures.base import APITestCase as BaseAPITestCase


class ReservationViewSetTest(BaseAPITestCase):
    """Test ReservationViewSet API endpoints"""

    def test_list_reservations(self):
        """Test listing all reservations"""
        # Create test reservations
        ReservationFactory(restaurant=self.restaurant)
        ConfirmedReservationFactory(restaurant=self.restaurant)

        # Make request
        response = self.client.get("/api/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Parse response
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)

        # Check response format
        reservation_data = data[0]
        self.assertIn("id", reservation_data)
        self.assertIn("status", reservation_data)
        self.assertIn("reservation_date", reservation_data)
        self.assertIn("reservation_time", reservation_data)

    def test_retrieve_reservation(self):
        """Test retrieving a specific reservation"""
        reservation = ReservationFactory(restaurant=self.restaurant)

        # Make request
        url = f"/api/{reservation.id}/"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Parse response
        data = response.json()
        self.assertEqual(data["id"], str(reservation.id))
        self.assertEqual(data["status"], reservation.status)
        self.assertIn("expires_at", data)

    def test_retrieve_nonexistent_reservation(self):
        """Test retrieving a reservation that doesn't exist"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        url = f"/api/{fake_id}/"

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertIn("error", data)

    @patch("reservations.views.TableReservationLock")
    def test_create_reservation_success(self, mock_lock):
        """Test creating a reservation successfully"""
        # Setup mocks

        # Mock the lock context manager properly
        mock_lock_instance = mock_lock.return_value
        mock_lock_instance.__enter__.return_value = mock_lock_instance
        mock_lock_instance.__exit__.return_value = None
        mock_lock_instance.extend_lock.return_value = None

        # Prepare data
        data = {
            "restaurant_id": self.restaurant.id,
            "customer_id": self.customer.id,
            "table_id": self.table.id,
            "reservation_date": "2025-09-15",
            "reservation_time": "19:00:00",
            "party_size": 4,
        }

        # Make request
        response = self.client.post("/api/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Parse response
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["status"], "pending")
        self.assertIn("expires_at", data)
        self.assertIn("message", data)

        # Verify reservation was created
        reservation = Reservation.objects.get(id=data["id"])
        self.assertEqual(reservation.party_size, 4)
        self.assertEqual(str(reservation.reservation_date), "2025-09-15")

    @patch("reservations.views.TableReservationLock")
    def test_create_reservation_table_unavailable(self, mock_lock):
        """Test creating reservation when table is unavailable"""
        # Mock the lock context manager properly
        mock_lock_instance = mock_lock.return_value
        mock_lock_instance.__enter__.return_value = mock_lock_instance
        mock_lock_instance.__exit__.return_value = None
        mock_lock_instance.extend_lock.return_value = None

        # Create a conflicting reservation to make table unavailable
        from datetime import date, time

        ReservationFactory(
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.CONFIRMED,
        )

        # Prepare data for conflicting reservation
        data = {
            "table_id": self.table.id,
            "reservation_date": "2025-09-15",
            "reservation_time": "19:00:00",
            "party_size": 2,
        }

        # Make request
        response = self.client.post("/api/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("no disponible", data["error"])

    def test_create_reservation_missing_fields(self):
        """Test creating reservation with missing required fields"""
        # Missing table_id
        data = {
            "reservation_date": "2025-09-15",
            "reservation_time": "19:00:00",
            "party_size": 2,
        }

        response = self.client.post("/api/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("campos requeridos", data["error"])

    @patch("reservations.views.TableReservationLock")
    def test_create_reservation_lock_error(self, mock_lock):
        """Test creating reservation when lock fails"""
        # Setup mock to raise exception
        mock_lock.side_effect = Exception("Lock acquisition failed")

        # Prepare data
        data = {
            "table_id": self.table.id,
            "reservation_date": "2025-09-15",
            "reservation_time": "19:00:00",
            "party_size": 2,
        }

        # Make request
        response = self.client.post("/api/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        self.assertIn("error", data)

    @patch("reservations.views.TableReservationLock")
    def test_create_reservation_validation_error(self, mock_lock):
        """Test creating reservation with validation error (double booking)"""
        # Setup mocks

        # Mock the lock context manager properly
        mock_lock_instance = mock_lock.return_value
        mock_lock_instance.__enter__.return_value = mock_lock_instance
        mock_lock_instance.__exit__.return_value = None
        mock_lock_instance.extend_lock.return_value = None

        # Create existing reservation first
        ReservationFactory(
            table=self.table,
            reservation_date=date(2025, 9, 15),
            reservation_time=time(19, 0),
            status=Reservation.Status.CONFIRMED,
        )

        # Try to create conflicting reservation
        data = {
            "restaurant_id": self.restaurant.id,
            "customer_id": self.customer.id,
            "table_id": self.table.id,
            "reservation_date": "2025-09-15",
            "reservation_time": "19:00:00",
            "party_size": 2,
        }

        response = self.client.post("/api/", data, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("no disponible", data["error"])


class ReservationAPIIntegrationTest(BaseAPITestCase):
    """Test API integration scenarios"""

    @patch("reservations.views.TableReservationLock")
    def test_concurrent_reservation_creation(self, mock_lock):
        """Test handling concurrent reservation attempts"""

        # Mock the lock context manager properly
        mock_lock_instance = mock_lock.return_value
        mock_lock_instance.__enter__.return_value = mock_lock_instance
        mock_lock_instance.__exit__.return_value = None
        mock_lock_instance.extend_lock.return_value = None

        data = {
            "restaurant_id": self.restaurant.id,
            "customer_id": self.customer.id,
            "table_id": self.table.id,
            "reservation_date": "2025-09-15",
            "reservation_time": "19:00:00",
            "party_size": 2,
        }

        # First request should succeed
        response1 = self.client.post("/api/", data, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second request should fail due to conflict
        response2 = self.client.post("/api/", data, format="json")
        self.assertEqual(response2.status_code, status.HTTP_409_CONFLICT)

    def test_reservation_lifecycle_via_api(self):
        """Test complete reservation lifecycle through API"""
        # Create reservation
        with (
            patch("reservations.views.TableReservationLock") as mock_lock,
        ):
            mock_avail.return_value = True

            # Mock the lock context manager properly
            mock_lock_instance = mock_lock.return_value
            mock_lock_instance.__enter__.return_value = mock_lock_instance
            mock_lock_instance.__exit__.return_value = None
            mock_lock_instance.extend_lock.return_value = None

            data = {
                "restaurant_id": self.restaurant.id,
                "customer_id": self.customer.id,
                "table_id": self.table.id,
                "reservation_date": "2025-09-15",
                "reservation_time": "19:00:00",
                "party_size": 2,
            }

            # Create
            response = self.client.post("/api/", data, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

            reservation_id = response.json()["id"]

            # Retrieve
            response = self.client.get(f"/api/{reservation_id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["status"], "pending")

            # List (should include our reservation)
            response = self.client.get("/api/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            reservation_ids = [r["id"] for r in response.json()]
            self.assertIn(reservation_id, reservation_ids)


class APIErrorHandlingTest(BaseAPITestCase):
    """Test API error handling scenarios"""

    def test_invalid_json_request(self):
        """Test handling invalid JSON in request"""
        response = self.client.post(
            "/api/", "invalid json", content_type="application/json"
        )

        # Django should handle this gracefully
        self.assertIn(response.status_code, [400, 500])

    def test_malformed_uuid_in_url(self):
        """Test handling malformed UUID in URL"""
        url = "/api/not-a-uuid/"
        response = self.client.get(url)

        # Should return 404, 400, or 500 (Django raises ValidationError on malformed UUID)
        self.assertIn(response.status_code, [400, 404, 500])

    @patch("reservations.views.Reservation.objects.create")
    def test_database_error_handling(self, mock_create):
        """Test handling database errors"""
        mock_create.side_effect = Exception("Database connection failed")

        with (
            patch("reservations.views.TableReservationLock") as mock_lock,
        ):
            mock_avail.return_value = True

            # Mock the lock context manager properly
            mock_lock_instance = mock_lock.return_value
            mock_lock_instance.__enter__.return_value = mock_lock_instance
            mock_lock_instance.__exit__.return_value = None
            mock_lock_instance.extend_lock.return_value = None

            data = {
                "table_id": self.table.id,
                "reservation_date": "2025-09-15",
                "reservation_time": "19:00:00",
                "party_size": 2,
            }

            response = self.client.post("/api/", data, format="json")
            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )

            data = response.json()
            self.assertIn("error", data)
