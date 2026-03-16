from pydantic import BaseModel


class VotesResponse(BaseModel):
    tea: int
    coffee: int


class VoteMeResponse(BaseModel):
    ip: str
    tea: int
    coffee: int


class VoteRequest(BaseModel):
    tea: int
    coffee: int


class ChatMessageOut(BaseModel):
    name: str
    message: str


class LoginRequest(BaseModel):
    name: str


class LoginResponse(BaseModel):
    success: bool
    name: str
    message: str


class AuthUser(BaseModel):
    """Authenticated user info"""

    id: int
    name: str
    ip_address: str


class ResetRequest(BaseModel):
    password: str


class UnbindRequest(BaseModel):
    name: str
    password: str


class UnbindResponse(BaseModel):
    success: bool
    name: str
    message: str


class UserOrderDetail(BaseModel):
    name: str
    tea: int
    coffee: int


class OrdersBreakdownResponse(BaseModel):
    orders: list[UserOrderDetail]
    total_tea: int
    total_coffee: int


class RemoveOrderRequest(BaseModel):
    name: str
    password: str


class RemoveOrderResponse(BaseModel):
    success: bool
    name: str
    message: str


class RemoveAllLoginsRequest(BaseModel):
    password: str


class RemoveAllLoginsResponse(BaseModel):
    success: bool
    count: int
    message: str
