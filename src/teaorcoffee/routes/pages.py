from fastapi import APIRouter
from fastapi.requests import Request
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")
templates = Jinja2Templates(directory=_TEMPLATES_DIR)


@router.get("/", include_in_schema=False)
async def login(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.get("/order", include_in_schema=False)
async def order(request: Request):
    return templates.TemplateResponse(request, "order.html")


@router.get("/admin", include_in_schema=False)
async def admin(request: Request):
    return templates.TemplateResponse(request, "admin.html")


@router.get("/hr", include_in_schema=False)
async def hr(request: Request):
    return templates.TemplateResponse(request, "hr.html")


@router.get("/office-admin", include_in_schema=False)
async def office_admin(request: Request):
    return templates.TemplateResponse(request, "office_admin.html")


@router.get("/distributor", include_in_schema=False)
async def distributor(request: Request):
    return templates.TemplateResponse(request, "distributor.html")


@router.get("/stats", include_in_schema=False)
async def stats(request: Request):
    return templates.TemplateResponse(request, "stats.html")
