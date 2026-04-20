from pydantic import BaseModel


class VotesResponse(BaseModel):
    tea: int
    coffee: int


class VoteMeResponse(BaseModel):
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
    password: str | None = None


class LoginResponse(BaseModel):
    success: bool
    name: str
    message: str
    token: str | None = None
    password_required: bool = False


class AuthUser(BaseModel):
    """Authenticated user info"""

    id: int
    name: str
    token: str


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


class SetUserDisabledRequest(BaseModel):
    name: str
    password: str
    disabled: bool


class SetUserDisabledResponse(BaseModel):
    success: bool
    name: str
    message: str


class AllowedNamesResponse(BaseModel):
    names: list[str]


class AddAllowedNameRequest(BaseModel):
    name: str
    password: str


class AddAllowedNameResponse(BaseModel):
    success: bool
    name: str
    message: str


class RemoveAllowedNameRequest(BaseModel):
    name: str
    password: str


class RemoveAllowedNameResponse(BaseModel):
    success: bool
    name: str
    message: str
