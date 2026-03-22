import unittest
from unittest.mock import AsyncMock, patch
from decimal import Decimal
import sys
import os

# Add the project root folder to Python paths to make file imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.account import Account
from services.notion_writer import NotionWriter


class TestNotionWriter(unittest.IsolatedAsyncioTestCase):
    @patch('services.notion_writer.AsyncClient')
    async def test_add_account_success(self, MockAsyncClient):
        """Test for successful addition of an account to Notion"""
        # Setup mock for successful Notion response
        mock_client_instance = MockAsyncClient.return_value
        mock_client_instance.pages.create = AsyncMock(return_value={})
        
        writer = NotionWriter()
        writer.client = mock_client_instance  # Replace client with mock
        writer.account_db_id = "test_db_id"

        # Create test account object
        test_account = Account(name="Test Account", initial_amount=Decimal("150.50"))

        # Call function
        result = await writer.add_account(test_account)

        # Assertions
        self.assertTrue(result)
        mock_client_instance.pages.create.assert_called_once()
        call_kwargs = mock_client_instance.pages.create.call_args.kwargs
        self.assertEqual(call_kwargs["parent"], {"database_id": "test_db_id"})
        self.assertIn("Account", call_kwargs["properties"])

    @patch('services.notion_writer.AsyncClient')
    async def test_add_account_failure(self, MockAsyncClient):
        """Test for handling errors during account addition to Notion"""
        # Setup mock to simulate Notion connection error
        mock_client_instance = MockAsyncClient.return_value
        mock_client_instance.pages.create.side_effect = Exception("API Connection Error")
        
        writer = NotionWriter()
        writer.client = mock_client_instance

        test_account = Account(name="Test", initial_amount=Decimal("0"))
        
        # Function should catch the error (through try/except) and safely return False
        result = await writer.add_account(test_account)
        self.assertFalse(result)

    @patch('services.notion_writer.AsyncClient')
    async def test_delete_account_success(self, MockAsyncClient):
        """Test for successful deletion (archival) of an account"""
        mock_client_instance = MockAsyncClient.return_value
        mock_client_instance.pages.update = AsyncMock(return_value={})
        
        writer = NotionWriter()
        writer.client = mock_client_instance

        result = await writer.delete_account("test_account_uuid_123")

        # Check if True is returned and archived=True parameter is sent
        self.assertTrue(result)
        mock_client_instance.pages.update.assert_called_once_with(
            page_id="test_account_uuid_123",
            archived=True
        )

    @patch('services.notion_writer.AsyncClient')
    async def test_delete_account_failure(self, MockAsyncClient):
        """Test for handling errors during account deletion"""
        mock_client_instance = MockAsyncClient.return_value
        mock_client_instance.pages.update.side_effect = Exception("API Error")
        
        writer = NotionWriter()
        writer.client = mock_client_instance

        result = await writer.delete_account("test_account_uuid_123")

        # Check that the error is caught and False is returned
        self.assertFalse(result)

    @patch('services.notion_writer.AsyncClient')
    async def test_get_accounts_success(self, MockAsyncClient):
        """Test for getting and correctly converting a list of accounts from Notion"""
        mock_client_instance = MockAsyncClient.return_value
        
        # Mock JSON response from Notion API
        mock_response = {
            "results": [
                {
                    "id": "uuid_account_1",
                    "properties": {
                        "Account": {"title": [{"text": {"content": "Monobank"}}]},
                        "Initial Amount": {"number": 1500.50}
                    }
                },
                {
                    "id": "uuid_account_2",
                    "properties": {
                        "Account": {"title": [{"text": {"content": "Готівка"}}]},
                        "Initial Amount": {"number": None}  # Mock empty value in database
                    }
                }
            ]
        }
        mock_client_instance.request = AsyncMock(return_value=mock_response)
        
        writer = NotionWriter()
        writer.client = mock_client_instance
        writer.account_db_id = "test_db_id"

        # Call function to get accounts
        accounts = await writer.get_accounts()

        # Should get a list of two parsed Account objects
        self.assertEqual(len(accounts), 2)
        
        # Check parsed data for the first account
        self.assertEqual(accounts[0].id, "uuid_account_1")
        self.assertEqual(accounts[0].name, "Monobank")
        self.assertEqual(accounts[0].initial_amount, Decimal("1500.50"))
        
        # Check parsed data for the second account (with missing initial amount)
        self.assertEqual(accounts[1].id, "uuid_account_2")
        self.assertEqual(accounts[1].name, "Готівка")
        # If the value in Notion is None, the program should recognize it as 0
        self.assertEqual(accounts[1].initial_amount, Decimal("0"))
        
        # Check correct API call with required parameters
        mock_client_instance.request.assert_called_once_with(
            path="databases/test_db_id/query",
            method="POST",
            body={}
        )

    @patch('services.notion_writer.AsyncClient')
    async def test_get_accounts_failure(self, MockAsyncClient):
        """Test for handling errors during account retrieval"""
        mock_client_instance = MockAsyncClient.return_value
        mock_client_instance.request.side_effect = Exception("API Server Error")
        
        writer = NotionWriter()
        writer.client = mock_client_instance

        # In case of Notion crash, the program should return an empty list (and not crash fatally)
        accounts = await writer.get_accounts()

        self.assertEqual(accounts, [])


if __name__ == '__main__':
    unittest.main()