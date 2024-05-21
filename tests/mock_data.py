# tests/mock_data.py

mock_users = [
    {
        "id": "1",
        "email": "user1@example.com",
        "role": "user",
        "tenant_id": "tenant1",
        "created_at": "2023-01-01T00:00:00Z"
    },
    {
        "id": "2",
        "email": "user2@example.com",
        "role": "admin",
        "tenant_id": "tenant2",
        "created_at": "2023-01-01T00:00:00Z"
    }
]

mock_user = {
    "id": "1",
    "email": "user1@example.com",
    "role": "user",
    "tenant_id": "tenant1",
    "created_at": "2023-01-01T00:00:00Z"
}

mock_new_user = {
    "id": "3",
    "email": "newuser@example.com",
    "role": "user",
    "tenant_id": "tenant3",
    "created_at": "2023-01-01T00:00:00Z"
}
