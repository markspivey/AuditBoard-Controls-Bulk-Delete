#!/usr/bin/env python3
"""
AuditBoard API Client
Centralized API client for all AuditBoard interactions.
"""
import os
import requests
import time
from typing import Optional, Dict, Any, List


class AuditBoardClient:
    """Centralized API client for AuditBoard with retry logic and error handling."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        Initialize AuditBoard API client.

        Args:
            base_url: AuditBoard API base URL (e.g., https://org.auditboardapp.com/api/v1)
            api_token: API authentication token
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.base_url = base_url or os.getenv('AUDITBOARD_BASE_URL')
        self.api_token = api_token or os.getenv('AUDITBOARD_API_TOKEN')

        if not self.base_url:
            raise ValueError("base_url or AUDITBOARD_BASE_URL environment variable required")
        if not self.api_token:
            raise ValueError("api_token or AUDITBOARD_API_TOKEN environment variable required")

        # Remove trailing slash from base_url
        self.base_url = self.base_url.rstrip('/')

        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        retry_count: int = 0
    ) -> requests.Response:
        """
        Make HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON body data
            retry_count: Current retry attempt

        Returns:
            Response object

        Raises:
            requests.RequestException: On request failure after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
                timeout=self.timeout
            )

            # Retry on server errors (5xx)
            if response.status_code >= 500 and retry_count < self.max_retries:
                time.sleep(self.retry_delay * (retry_count + 1))
                return self._make_request(method, endpoint, params, json_data, retry_count + 1)

            return response

        except requests.RequestException as e:
            if retry_count < self.max_retries:
                time.sleep(self.retry_delay * (retry_count + 1))
                return self._make_request(method, endpoint, params, json_data, retry_count + 1)
            raise

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        GET request.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            requests.HTTPError: On HTTP error status
        """
        response = self._make_request('GET', endpoint, params=params)
        response.raise_for_status()
        return response.json()

    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST request.

        Args:
            endpoint: API endpoint
            data: JSON body data

        Returns:
            JSON response data

        Raises:
            requests.HTTPError: On HTTP error status
        """
        response = self._make_request('POST', endpoint, json_data=data)
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint: str) -> bool:
        """
        DELETE request.

        Args:
            endpoint: API endpoint

        Returns:
            True if successful (200/204), False otherwise

        Raises:
            requests.HTTPError: On non-success HTTP status
        """
        response = self._make_request('DELETE', endpoint)

        if response.status_code in [200, 204]:
            return True

        response.raise_for_status()
        return False

    # Convenience methods for common resources

    def get_controls(self, params: Optional[Dict] = None) -> List[Dict]:
        """Get all controls."""
        data = self.get('controls', params)
        return data.get('controls', [])

    def get_control(self, control_id: int) -> Optional[Dict]:
        """Get a specific control by ID."""
        try:
            data = self.get(f'controls/{control_id}')
            controls = data.get('controls', [])
            return controls[0] if controls else None
        except requests.HTTPError:
            return None

    def get_processes(self, params: Optional[Dict] = None) -> List[Dict]:
        """Get all processes."""
        data = self.get('processes', params)
        return data.get('processes', [])

    def get_process(self, process_id: int) -> Optional[Dict]:
        """Get a specific process by ID."""
        try:
            data = self.get(f'processes/{process_id}')
            processes = data.get('processes', [])
            return processes[0] if processes else None
        except requests.HTTPError:
            return None

    def get_subprocesses(self, params: Optional[Dict] = None) -> List[Dict]:
        """Get all subprocesses."""
        data = self.get('subprocesses', params)
        return data.get('subprocesses', [])

    def get_subprocess(self, subprocess_id: int) -> Optional[Dict]:
        """Get a specific subprocess by ID."""
        try:
            data = self.get(f'subprocesses/{subprocess_id}')
            subprocesses = data.get('subprocesses', [])
            return subprocesses[0] if subprocesses else None
        except requests.HTTPError:
            return None

    def get_entities(self, params: Optional[Dict] = None) -> List[Dict]:
        """Get all entities."""
        data = self.get('entities', params)
        return data.get('entities', [])

    def get_entity(self, entity_id: int) -> Optional[Dict]:
        """Get a specific entity by ID."""
        try:
            data = self.get(f'entities/{entity_id}')
            entities = data.get('entities', [])
            return entities[0] if entities else None
        except requests.HTTPError:
            return None

    def get_regions(self, params: Optional[Dict] = None) -> List[Dict]:
        """Get all regions."""
        data = self.get('regions', params)
        return data.get('regions', [])

    def get_region(self, region_id: int) -> Optional[Dict]:
        """Get a specific region by ID."""
        try:
            data = self.get(f'regions/{region_id}')
            regions = data.get('regions', [])
            return regions[0] if regions else None
        except requests.HTTPError:
            return None

    def get_auditable_entities(self, params: Optional[Dict] = None) -> List[Dict]:
        """Get all auditable entities."""
        data = self.get('auditable_entities', params)
        return data.get('auditable_entities', [])

    def get_auditable_entity(self, entity_id: int) -> Optional[Dict]:
        """Get a specific auditable entity by ID."""
        try:
            data = self.get(f'auditable_entities/{entity_id}')
            entities = data.get('auditable_entities', [])
            return entities[0] if entities else None
        except requests.HTTPError:
            return None

    def delete_control(self, control_id: int) -> bool:
        """Delete a control by ID."""
        return self.delete(f'controls/{control_id}')

    def delete_subprocess(self, subprocess_id: int) -> bool:
        """Delete a subprocess by ID."""
        return self.delete(f'subprocesses/{subprocess_id}')

    def delete_process(self, process_id: int) -> bool:
        """Delete a process by ID."""
        return self.delete(f'processes/{process_id}')

    def delete_entity(self, entity_id: int) -> bool:
        """Delete an entity by ID."""
        return self.delete(f'entities/{entity_id}')

    def delete_region(self, region_id: int) -> bool:
        """Delete a region by ID."""
        return self.delete(f'regions/{region_id}')
