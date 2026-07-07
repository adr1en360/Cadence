from fastapi import APIRouter, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import PlainTextResponse, FileResponse
import os

router = APIRouter(tags=["Developer Portal"])
templates = Jinja2Templates(directory="templates")

@router.get("/developer")
def dev_intro(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="developer/introduction.html",
        context={"active_page": "introduction"}
    )

@router.get("/developer/authentication")
def dev_auth(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="developer/authentication.html",
        context={"active_page": "authentication"}
    )

@router.get("/developer/plans")
def dev_plans(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="developer/plans.html",
        context={"active_page": "plans"}
    )

@router.get("/developer/subscriptions")
def dev_subs(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="developer/subscriptions.html",
        context={"active_page": "subscriptions"}
    )

@router.get("/developer/webhooks")
def dev_webhooks(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="developer/webhooks.html",
        context={"active_page": "webhooks"}
    )

@router.get("/developer/errors")
def dev_errors(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="developer/errors.html",
        context={"active_page": "errors"}
    )

@router.get("/developer/payments")
def dev_payments(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="developer/payments.html",
        context={"active_page": "payments"}
    )

@router.get("/llms.txt", response_class=PlainTextResponse)
def get_static_llms_txt():
    """Serve the plain text llms.txt guide for AI agents from static/llms.txt."""
    file_path = os.path.join("static", "llms.txt")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="Agent documentation not found")
