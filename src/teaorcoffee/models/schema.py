from pydantic import BaseModel
from typing import Optional


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    name: str
    password: str | None = None
    company_id: str | None = None


class LoginResponse(BaseModel):
    success: bool
    name: str
    message: str
    token: str | None = None
    password_required: bool = False
    nickname: str | None = None
    role: str = "employee"
    company_id: str | None = None
    company_name: str | None = None
    company_mode: str | None = None


class AuthUser(BaseModel):
    id: int
    name: str
    token: str
    role: str = "employee"
    company_id: str | None = None
    nickname: str | None = None


# ── Companies ─────────────────────────────────────────────────────────────────

class CompanyOut(BaseModel):
    id: str
    name: str
    slug: str
    mode: str
    address: str = ""
    distributor_id: str | None = None
    is_active: bool


class CreateCompanyRequest(BaseModel):
    name: str
    slug: str
    mode: str
    address: str = ""
    distributor_id: str | None = None


class UpdateCompanyRequest(BaseModel):
    company_id: str
    name: str


class UpdateCompanyAddressRequest(BaseModel):
    company_id: str
    address: str


class SetMyAddressRequest(BaseModel):
    address: str


class SetMyDistributorRequest(BaseModel):
    distributor_id: str


class CompanyActiveRequest(BaseModel):
    company_id: str
    is_active: bool


class SetCompanyDistributorRequest(BaseModel):
    company_id: str
    distributor_id: str


class SetCompanyModeRequest(BaseModel):
    company_id: str
    mode: str


class NewProductInput(BaseModel):
    name: str
    price: float


class RegisterCompanyRequest(BaseModel):
    name: str
    slug: str
    mode: str                              # "company" | "distributor"
    address: str = ""                      # differentiates branches sharing the same `name`
    distributor_id: str | None = None      # required if mode == "company"
    admin_name: str
    admin_password: str | None = None      # if omitted, admin sets password on first login
    manager_names: list[str] = []
    hr_names: list[str] = []
    staff_names: list[str] = []            # employees (company mode) or distributor boys (distributor mode)
    new_products: list[NewProductInput] = []   # mode == "company": reused if the chosen distributor already
                                                # has a product with that name, else created in their catalog.
                                                # mode == "distributor": seeds this new distributor's own catalog.


class RegisterCompanyResponse(BaseModel):
    success: bool
    company_id: str
    name: str
    message: str


# ── Distributor Products / Pricing ───────────────────────────────────────────

class DistributorProductOut(BaseModel):
    id: str
    name: str
    emoji: str
    current_price: float
    max_qty: int
    is_active: bool


class ProductNameSuggestion(BaseModel):
    name: str
    emoji: str
    price: float


class ProductSearchResponse(BaseModel):
    products: list[ProductNameSuggestion]


class AddDistributorProductRequest(BaseModel):
    company_id: str
    name: str
    emoji: str
    price: float
    max_qty: int


class UpdateDistributorProductRequest(BaseModel):
    product_id: str
    name: str
    emoji: str
    max_qty: int


class UpdateProductPriceRequest(BaseModel):
    product_id: str
    new_price: float


class ProductActiveRequest(BaseModel):
    product_id: str
    is_active: bool


class PriceHistoryEntry(BaseModel):
    id: str
    price: float
    changed_by_user_id: int | None = None
    effective_at: str


class PriceHistoryResponse(BaseModel):
    history: list[PriceHistoryEntry]


# ── Company Product Enablement ───────────────────────────────────────────────

class CompanyProductOut(BaseModel):
    distributor_product_id: str
    name: str
    emoji: str
    price: float
    max_qty: int
    is_enabled: bool


class EnableCompanyProductRequest(BaseModel):
    distributor_product_id: str
    max_qty_override: int | None = None


class DisableCompanyProductRequest(BaseModel):
    distributor_product_id: str


class SetCompanyProductMaxQtyRequest(BaseModel):
    distributor_product_id: str
    max_qty: int | None = None


# ── Votes / Orders ────────────────────────────────────────────────────────────

class VoteRequest(BaseModel):
    product_id: str
    qty: int
    date: str | None = None


class EditVoteRequest(BaseModel):
    product_id: str
    qty: int
    date: str | None = None


class VoteActionResponse(BaseModel):
    success: bool
    message: str


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
    date: str
    status: str


class OrderDetail(BaseModel):
    name: str
    product_name: str
    product_emoji: str
    qty: int
    status: str = "delivered"


class OrdersBreakdownResponse(BaseModel):
    orders: list[OrderDetail]
    totals: dict[str, ProductTotal]
    order_count: int


class MyOrderEntry(BaseModel):
    id: str
    date: str
    product_id: str
    product_name: str
    product_emoji: str
    qty: int
    status: str


class MyOrdersResponse(BaseModel):
    orders: list[MyOrderEntry]


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessageOut(BaseModel):
    name: str
    message: str


# ── Admin / Shared ────────────────────────────────────────────────────────────

class ResetRequest(BaseModel):
    company_id: str | None = None


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
    company_id: str | None = None


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


class PlaceOrderForUserRequest(BaseModel):
    name: str
    product_id: str
    qty: int
    date: str | None = None


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
    company_id: str | None = None
    is_disabled: int
    nickname: str | None = None


class UsersListResponse(BaseModel):
    users: list[UserOut]


class AddCompanyMemberRequest(BaseModel):
    name: str
    company_id: str
    role: str


class AddCompanyMemberResponse(BaseModel):
    success: bool
    name: str
    message: str


class RemoveCompanyMemberRequest(BaseModel):
    user_id: int


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

class ProductSummaryRow(BaseModel):
    product_name: str
    delivered_qty: int
    delivered_count: int
    pending_qty: int
    pending_count: int


class CompanySummaryRow(BaseModel):
    company_name: str
    company_address: str = ""
    delivered_qty: int
    delivered_count: int
    pending_qty: int
    pending_count: int


class UserSummaryRow(BaseModel):
    user_name: str
    delivered_qty: int
    delivered_count: int
    pending_qty: int
    pending_count: int


class DistributorOrderSummaryResponse(BaseModel):
    by_product: list[ProductSummaryRow]
    by_company: list[CompanySummaryRow]
    by_user: list[UserSummaryRow]


class PendingOrderRow(BaseModel):
    id: str
    user_name: str
    company_name: str
    company_address: str = ""
    company_id: str
    product_name: str
    product_emoji: str
    qty: int
    date: str


class PendingOrdersResponse(BaseModel):
    orders: list[PendingOrderRow]


class DeliverOrderResponse(BaseModel):
    success: bool
    message: str
