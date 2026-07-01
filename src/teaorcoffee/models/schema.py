from pydantic import BaseModel
from typing import Optional


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    name: str
    password: str | None = None
    office_id: str | None = None


class LoginResponse(BaseModel):
    success: bool
    name: str
    message: str
    token: str | None = None
    password_required: bool = False
    nickname: str | None = None
    role: str = "user"
    office_id: str | None = None
    office_name: str | None = None
    company_id: str | None = None
    position: str | None = None


class AuthUser(BaseModel):
    id: int
    name: str
    token: str
    role: str = "user"
    office_id: str | None = None
    company_id: str | None = None
    position: str | None = None
    nickname: str | None = None


# ── Setup ─────────────────────────────────────────────────────────────────────

class SetupStatusResponse(BaseModel):
    needs_setup: bool


class SetupRequest(BaseModel):
    name: str
    password: str


class SetupResponse(BaseModel):
    success: bool
    message: str


# ── Office Requests ───────────────────────────────────────────────────────────

class OfficeRequestCreate(BaseModel):
    office_name: str
    requester_name: str
    contact_info: str


class OfficeRequestOut(BaseModel):
    id: str
    office_name: str
    requester_name: str
    contact_info: str
    status: str
    created_at: str


# ── Offices ───────────────────────────────────────────────────────────────────

class OfficeOut(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool


class CreateOfficeRequest(BaseModel):
    name: str
    slug: str


class UpdateOfficeRequest(BaseModel):
    office_id: str
    name: str


class OfficeActiveRequest(BaseModel):
    office_id: str
    is_active: bool


class CreateFullOfficeRequest(BaseModel):
    name: str
    slug: str
    employee_names: list[str] = []
    admin_names: list[str] = []
    hr_names: list[str] = []
    approve_request_id: str | None = None


class CreateFullOfficeResponse(BaseModel):
    success: bool
    office_id: str
    name: str
    message: str


# ── Products ──────────────────────────────────────────────────────────────────

class ProductOut(BaseModel):
    id: str
    name: str
    emoji: str
    max_qty: int
    is_active: bool
    sort_order: int


class AddProductRequest(BaseModel):
    office_id: str
    name: str
    emoji: str
    max_qty: int


class UpdateProductRequest(BaseModel):
    product_id: str
    name: str
    emoji: str
    max_qty: int


class ProductActiveRequest(BaseModel):
    product_id: str
    is_active: bool


# ── Votes / Orders ────────────────────────────────────────────────────────────

class VoteRequest(BaseModel):
    product_id: str
    qty: int


class ProductTotal(BaseModel):
    total: int
    emoji: str


class VotesResponse(BaseModel):
    totals: dict[str, ProductTotal]
    order_count: int


class VoteMeResponse(BaseModel):
    product_id: str
    product_name: str
    product_emoji: str
    qty: int


class OrderDetail(BaseModel):
    name: str
    product_name: str
    product_emoji: str
    qty: int


class OrdersBreakdownResponse(BaseModel):
    orders: list[OrderDetail]
    totals: dict[str, ProductTotal]
    order_count: int


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessageOut(BaseModel):
    name: str
    message: str


# ── Admin / Shared ────────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    office_id: str | None = None


class UnbindRequest(BaseModel):
    name: str


class UnbindResponse(BaseModel):
    success: bool
    name: str
    message: str


class RemoveOrderRequest(BaseModel):
    name: str


class RemoveOrderResponse(BaseModel):
    success: bool
    name: str
    message: str


class RemoveAllLoginsRequest(BaseModel):
    office_id: str | None = None


class RemoveAllLoginsResponse(BaseModel):
    success: bool
    count: int
    message: str


class SetUserDisabledRequest(BaseModel):
    name: str
    disabled: bool


class SetUserDisabledResponse(BaseModel):
    success: bool
    name: str
    message: str


class PendingPasswordUsersResponse(BaseModel):
    users: list[str]
    count: int


class UpdateUserNameRequest(BaseModel):
    old_name: str
    new_name: str


class UpdateUserNameResponse(BaseModel):
    success: bool
    old_name: str
    new_name: str
    message: str


class AllowedNamesResponse(BaseModel):
    names: list[str]


class AddAllowedNameRequest(BaseModel):
    name: str
    office_id: str | None = None


class AddAllowedNameResponse(BaseModel):
    success: bool
    name: str
    message: str


class RemoveAllowedNameRequest(BaseModel):
    name: str


class RemoveAllowedNameResponse(BaseModel):
    success: bool
    name: str
    message: str


class PlaceOrderForUserRequest(BaseModel):
    name: str
    product_id: str
    qty: int


class PlaceOrderForUserResponse(BaseModel):
    success: bool
    name: str
    message: str


class SetNicknameRequest(BaseModel):
    name: str
    nickname: str | None = None


class SetNicknameResponse(BaseModel):
    success: bool
    name: str
    nickname: str | None
    message: str


class SetUserRoleRequest(BaseModel):
    name: str
    role: str


class SetUserRoleResponse(BaseModel):
    success: bool
    name: str
    role: str
    message: str


class UserOut(BaseModel):
    id: int
    name: str
    role: str
    office_id: str | None = None
    company_id: str | None = None
    position: str | None = None
    is_disabled: int
    nickname: str | None = None


class UsersListResponse(BaseModel):
    users: list[UserOut]


# ── Stats ─────────────────────────────────────────────────────────────────────

class DailyTotals(BaseModel):
    date: str
    tea: int
    coffee: int
    products: dict[str, int] = {}


class StatsRangeResponse(BaseModel):
    days: list[DailyTotals]


class UserOrderDetail(BaseModel):
    name: str
    tea: int
    coffee: int
    product_name: str = ""
    product_emoji: str = ""
    qty: int = 0


class UserOrdersForDateResponse(BaseModel):
    date: str
    orders: list[UserOrderDetail]
    total_tea: int
    total_coffee: int
    totals: dict[str, int] = {}


class UserStatsDayEntry(BaseModel):
    date: str
    tea: int
    coffee: int
    product_name: str = ""
    qty: int = 0


class UserStatsResponse(BaseModel):
    name: str
    start: str
    end: str
    days: list[UserStatsDayEntry]
    total_tea: int
    total_coffee: int
    order_days: int


class UserNamesResponse(BaseModel):
    names: list[str]


# ── Distributor ───────────────────────────────────────────────────────────────

class DistributorCompanyOut(BaseModel):
    id: str
    name: str
    office_id: str
    is_active: bool


class CreateCompanyRequest(BaseModel):
    name: str
    office_id: str


class PositionOut(BaseModel):
    id: str
    name: str
    level: int


class AddPositionRequest(BaseModel):
    company_id: str
    name: str
    level: int


class RemovePositionRequest(BaseModel):
    position_id: str


class DistributorStaffOut(BaseModel):
    id: int
    name: str
    role: str
    position: str | None = None
    is_disabled: int


class AddStaffRequest(BaseModel):
    company_id: str
    name: str
    role: str
    position: str


class RemoveStaffRequest(BaseModel):
    user_id: int
