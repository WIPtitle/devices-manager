import os
from typing import List

import httpx
from sqlmodel import SQLModel


class UserResponse(SQLModel):
    id: int
    email: str
    permissions: List[str]


class AuthClient:
    def __init__(self):
        self.auth_hostname = os.getenv("AUTH_HOSTNAME")

    async def check_pin(self, token: str, pin: str):
        url = f"http://{self.auth_hostname}:8000/user"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json={"pin": pin}, headers={"Authorization": f"Bearer {token}"})
                response.raise_for_status()
                user = response.json()
                user_response = UserResponse(**user)
                return True
        except httpx.HTTPStatusError:
            return False
