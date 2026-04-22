from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import ValidationError
from sqlalchemy import select

from app.core.csrf import enforce_csrf_protection, get_or_create_csrf_token
from app.core.dependencies import AppSettings, DBSession, OptionalCurrentUser
from app.core.templating import templates
from app.models.category import Category
from app.models.enums import MembershipStatus, MembershipTier, OrderStatus, ProductStatus, Role, VendorStatus
from app.models.user import User
from app.models.vendor import Vendor
from app.schemas.auth import LoginRequest, SignupRequest
from app.schemas.platform import (
    AddCartItemRequest,
    AdminProductStatusUpdateRequest,
    CheckoutRequest,
    MembershipCreateRequest,
    OrderStatusUpdateRequest,
    PaymentSimulationRequest,
    UpdateCartItemRequest,
    VendorAdminUpdateRequest,
    VendorProductCreateRequest,
)
from app.services import admin as admin_service
from app.services import dashboard as dashboard_service
from app.services import orders as order_service
from app.services.uploads import save_validated_product_image
from app.services import user as user_service
from app.services import vendor as vendor_service
from app.services.auth import authenticate_user, clear_session, establish_session, register_user
from app.utils.flash import flash, pop_flashes


router = APIRouter(
    include_in_schema=False,
    dependencies=[Depends(enforce_csrf_protection)],
)


@router.get("/", response_class=HTMLResponse, name="home_page")
def home_page(request: Request, current_user: OptionalCurrentUser) -> Response:
    if current_user is not None:
        return RedirectResponse(url=_dashboard_path(request, current_user.role), status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url=str(request.url_for("login_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse, name="login_page")
def login_page(request: Request, current_user: OptionalCurrentUser) -> Response:
    if current_user is not None:
        return RedirectResponse(url=_dashboard_path(request, current_user.role), status_code=status.HTTP_303_SEE_OTHER)

    return _render(
        request,
        "login.html",
        current_user=current_user,
        form_values={"email": ""},
    )


@router.post("/login", response_class=HTMLResponse, name="login_submit")
def login_submit(
    request: Request,
    db: DBSession,
    email: str = Form(...),
    password: str = Form(...),
) -> Response:
    try:
        payload = LoginRequest(email=email, password=password)
        user = authenticate_user(db, payload)
        establish_session(request, user)
        flash(request, f"Welcome back, {user.name}.", "success")
        return RedirectResponse(url=_dashboard_path(request, user.role), status_code=status.HTTP_303_SEE_OTHER)
    except (HTTPException, ValidationError) as exc:
        flash(request, _message_from_exception(exc), "danger")
        return _render(
            request,
            "login.html",
            current_user=None,
            form_values={"email": email.strip()},
            status_code=_status_from_exception(exc),
        )


@router.get("/signup", response_class=HTMLResponse, name="signup_page")
def signup_page(request: Request, current_user: OptionalCurrentUser, db: DBSession) -> Response:
    if current_user is not None:
        return RedirectResponse(url=_dashboard_path(request, current_user.role), status_code=status.HTTP_303_SEE_OTHER)

    return _render(
        request,
        "signup.html",
        current_user=current_user,
        categories=_active_categories(db),
        form_values={
            "name": "",
            "email": "",
            "role": Role.USER.value,
            "business_name": "",
            "contact_phone": "",
            "vendor_description": "",
            "category_id": "",
            "admin_signup_code": "",
        },
    )


@router.post("/signup", response_class=HTMLResponse, name="signup_submit")
def signup_submit(
    request: Request,
    db: DBSession,
    settings: AppSettings,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form(Role.USER.value),
    admin_signup_code: str = Form(""),
    business_name: str = Form(""),
    contact_phone: str = Form(""),
    vendor_description: str = Form(""),
    category_id: str = Form(""),
) -> Response:
    form_values = {
        "name": name.strip(),
        "email": email.strip(),
        "role": role,
        "business_name": business_name.strip(),
        "contact_phone": contact_phone.strip(),
        "vendor_description": vendor_description.strip(),
        "category_id": category_id.strip(),
        "admin_signup_code": admin_signup_code.strip(),
    }

    try:
        payload = SignupRequest(
            name=name,
            email=email,
            password=password,
            confirm_password=confirm_password,
            role=Role(role),
            admin_signup_code=admin_signup_code or None,
            business_name=business_name or None,
            contact_phone=contact_phone or None,
            vendor_description=vendor_description or None,
            category_id=_optional_int(category_id),
        )
        user = register_user(db, settings, payload)
        establish_session(request, user)
        flash(request, f"Account created successfully for {user.name}.", "success")
        return RedirectResponse(url=_dashboard_path(request, user.role), status_code=status.HTTP_303_SEE_OTHER)
    except (HTTPException, ValidationError, ValueError) as exc:
        flash(request, _message_from_exception(exc), "danger")
        return _render(
            request,
            "signup.html",
            current_user=None,
            categories=_active_categories(db),
            form_values=form_values,
            status_code=_status_from_exception(exc),
        )


@router.post("/logout", name="logout_submit")
def logout_submit(request: Request) -> RedirectResponse:
    clear_session(request)
    flash(request, "You have been logged out.", "info")
    return RedirectResponse(url=str(request.url_for("login_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard", name="dashboard_redirect")
def dashboard_redirect(request: Request, current_user: OptionalCurrentUser) -> Response:
    guard = _guard_page_user(request, current_user)
    if isinstance(guard, Response):
        return guard
    return RedirectResponse(url=_dashboard_path(request, guard.role), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard/admin", response_class=HTMLResponse, name="admin_dashboard_page")
def admin_dashboard_page(request: Request, current_user: OptionalCurrentUser, db: DBSession) -> Response:
    guard = _guard_page_user(request, current_user, Role.ADMIN)
    if isinstance(guard, Response):
        return guard

    dashboard_data = dashboard_service.get_admin_dashboard_data(db)
    membership_candidate_users = list(
        db.execute(select(User).order_by(User.name.asc()).limit(50)).scalars().all()
    )
    return _render(
        request,
        "dashboard_admin.html",
        current_user=guard,
        membership_candidate_users=membership_candidate_users,
        membership_tiers=list(MembershipTier),
        vendor_statuses=list(VendorStatus),
        product_statuses=[ProductStatus.APPROVED, ProductStatus.REJECTED, ProductStatus.ARCHIVED],
        **dashboard_data,
    )


@router.post("/dashboard/admin/vendors/{vendor_id}/status", name="admin_vendor_status_submit")
def admin_vendor_status_submit(
    request: Request,
    vendor_id: int,
    current_user: OptionalCurrentUser,
    db: DBSession,
    status_value: str = Form(..., alias="status"),
) -> Response:
    guard = _guard_page_user(request, current_user, Role.ADMIN)
    if isinstance(guard, Response):
        return guard

    try:
        admin_service.update_vendor(
            db,
            vendor_id=vendor_id,
            payload=VendorAdminUpdateRequest(status=VendorStatus(status_value)),
        )
        flash(request, "Vendor status updated.", "success")
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")

    return RedirectResponse(url=str(request.url_for("admin_dashboard_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/dashboard/admin/products/{product_id}/status", name="admin_product_status_submit")
def admin_product_status_submit(
    request: Request,
    product_id: int,
    current_user: OptionalCurrentUser,
    db: DBSession,
    status_value: str = Form(..., alias="status"),
    notes: str = Form(""),
) -> Response:
    guard = _guard_page_user(request, current_user, Role.ADMIN)
    if isinstance(guard, Response):
        return guard

    try:
        admin_service.update_product_status(
            db,
            product_id=product_id,
            actor_user_id=guard.id,
            payload=AdminProductStatusUpdateRequest(
                status=ProductStatus(status_value),
                notes=notes or None,
            ),
        )
        flash(request, "Product moderation status updated.", "success")
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")

    return RedirectResponse(url=str(request.url_for("admin_dashboard_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/dashboard/admin/memberships", name="admin_membership_submit")
def admin_membership_submit(
    request: Request,
    current_user: OptionalCurrentUser,
    db: DBSession,
    user_id: int = Form(...),
    tier: str = Form(...),
    price: str = Form(...),
    auto_renew: bool = Form(False),
) -> Response:
    guard = _guard_page_user(request, current_user, Role.ADMIN)
    if isinstance(guard, Response):
        return guard

    try:
        admin_service.create_membership(
            db,
            payload=MembershipCreateRequest(
                user_id=user_id,
                tier=MembershipTier(tier),
                price=price,
                auto_renew=auto_renew,
                status=MembershipStatus.ACTIVE,
            ),
        )
        flash(request, "Membership created successfully.", "success")
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")

    return RedirectResponse(url=str(request.url_for("admin_dashboard_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/dashboard/admin/orders/{order_id}/status", name="admin_order_status_submit")
def admin_order_status_submit(
    request: Request,
    order_id: int,
    current_user: OptionalCurrentUser,
    db: DBSession,
    status_value: str = Form(..., alias="status"),
    notes: str = Form(""),
) -> Response:
    guard = _guard_page_user(request, current_user, Role.ADMIN)
    if isinstance(guard, Response):
        return guard

    try:
        order_service.update_order_status(
            db,
            actor_user=guard,
            order_id=order_id,
            payload=OrderStatusUpdateRequest(status=OrderStatus(status_value), notes=notes or None),
        )
        flash(request, "Order status updated.", "success")
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")

    return RedirectResponse(url=str(request.url_for("admin_dashboard_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard/vendor", response_class=HTMLResponse, name="vendor_dashboard_page")
def vendor_dashboard_page(request: Request, current_user: OptionalCurrentUser, db: DBSession) -> Response:
    guard = _guard_page_user(request, current_user, Role.VENDOR)
    if isinstance(guard, Response):
        return guard

    dashboard_data = dashboard_service.get_vendor_dashboard_data(db, guard)
    return _render(
        request,
        "dashboard_vendor.html",
        current_user=guard,
        categories=_active_categories(db),
        order_statuses=[OrderStatus.READY, OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED],
        **dashboard_data,
    )


@router.post("/dashboard/vendor/products", name="vendor_product_submit")
async def vendor_product_submit(
    request: Request,
    current_user: OptionalCurrentUser,
    db: DBSession,
    category_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    unit_price: str = Form(...),
    inventory_count: int = Form(0),
    image_url: str = Form(""),
    product_image: UploadFile | None = File(default=None),
) -> Response:
    guard = _guard_page_user(request, current_user, Role.VENDOR)
    if isinstance(guard, Response):
        return guard

    try:
        resolved_image_url = image_url or None
        if product_image is not None and product_image.filename:
            resolved_image_url = await save_validated_product_image(product_image)

        vendor_service.create_vendor_product(
            db,
            vendor_user=guard,
            payload=VendorProductCreateRequest(
                category_id=category_id,
                name=name,
                description=description or None,
                unit_price=unit_price,
                inventory_count=inventory_count,
                image_url=resolved_image_url,
            ),
        )
        flash(request, "Product submitted successfully.", "success")
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")

    return RedirectResponse(url=str(request.url_for("vendor_dashboard_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/dashboard/vendor/orders/{order_id}/status", name="vendor_order_status_submit")
def vendor_order_status_submit(
    request: Request,
    order_id: int,
    current_user: OptionalCurrentUser,
    db: DBSession,
    status_value: str = Form(..., alias="status"),
    notes: str = Form(""),
) -> Response:
    guard = _guard_page_user(request, current_user, Role.VENDOR)
    if isinstance(guard, Response):
        return guard

    try:
        order_service.update_order_status(
            db,
            actor_user=guard,
            order_id=order_id,
            payload=OrderStatusUpdateRequest(status=OrderStatus(status_value), notes=notes or None),
        )
        flash(request, "Order status updated.", "success")
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")

    return RedirectResponse(url=str(request.url_for("vendor_dashboard_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard/user", response_class=HTMLResponse, name="user_dashboard_page")
def user_dashboard_page(request: Request, current_user: OptionalCurrentUser, db: DBSession) -> Response:
    guard = _guard_page_user(request, current_user, Role.USER)
    if isinstance(guard, Response):
        return guard

    dashboard_data = dashboard_service.get_user_dashboard_data(db, guard)
    return _render(request, "dashboard_user.html", current_user=guard, **dashboard_data)


@router.get("/products", response_class=HTMLResponse, name="products_page")
def products_page(
    request: Request,
    current_user: OptionalCurrentUser,
    db: DBSession,
    search: str | None = None,
    category_id: int | None = None,
    vendor_id: int | None = None,
) -> Response:
    guard = _guard_page_user(request, current_user, Role.USER)
    if isinstance(guard, Response):
        return guard

    products = user_service.browse_products(
        db,
        search=search,
        category_id=category_id,
        vendor_id=vendor_id,
    )
    approved_vendors = list(
        db.execute(
            select(Vendor)
            .where(Vendor.status == VendorStatus.APPROVED)
            .order_by(Vendor.business_name.asc())
        )
        .scalars()
        .all()
    )
    return _render(
        request,
        "products.html",
        current_user=guard,
        products=products,
        categories=_active_categories(db),
        approved_vendors=approved_vendors,
        selected_search=search or "",
        selected_category_id=category_id,
        selected_vendor_id=vendor_id,
    )


@router.post("/products/{product_id}/add-to-cart", name="product_add_to_cart_submit")
def product_add_to_cart_submit(
    request: Request,
    product_id: int,
    current_user: OptionalCurrentUser,
    db: DBSession,
    quantity: int = Form(1),
    return_to: str = Form("/products"),
) -> Response:
    guard = _guard_page_user(request, current_user, Role.USER)
    if isinstance(guard, Response):
        return guard

    try:
        user_service.add_item_to_cart(
            db,
            user=guard,
            payload=AddCartItemRequest(product_id=product_id, quantity=quantity),
        )
        flash(request, "Item added to cart.", "success")
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")

    return RedirectResponse(
        url=_safe_local_path(request, return_to, "products_page"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/cart", response_class=HTMLResponse, name="cart_page")
def cart_page(request: Request, current_user: OptionalCurrentUser, db: DBSession) -> Response:
    guard = _guard_page_user(request, current_user, Role.USER)
    if isinstance(guard, Response):
        return guard

    cart = user_service.get_active_cart(db, user_id=guard.id)
    return _render(request, "cart.html", current_user=guard, cart=cart)


@router.post("/cart/items/{cart_item_id}/update", name="cart_item_update_submit")
def cart_item_update_submit(
    request: Request,
    cart_item_id: int,
    current_user: OptionalCurrentUser,
    db: DBSession,
    quantity: int = Form(...),
) -> Response:
    guard = _guard_page_user(request, current_user, Role.USER)
    if isinstance(guard, Response):
        return guard

    try:
        user_service.update_cart_item_quantity(
            db,
            user=guard,
            cart_item_id=cart_item_id,
            payload=UpdateCartItemRequest(quantity=quantity),
        )
        flash(request, "Cart item updated.", "success")
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")

    return RedirectResponse(url=str(request.url_for("cart_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.post("/cart/items/{cart_item_id}/remove", name="cart_item_remove_submit")
def cart_item_remove_submit(
    request: Request,
    cart_item_id: int,
    current_user: OptionalCurrentUser,
    db: DBSession,
) -> Response:
    guard = _guard_page_user(request, current_user, Role.USER)
    if isinstance(guard, Response):
        return guard

    try:
        user_service.remove_cart_item(db, user=guard, cart_item_id=cart_item_id)
        flash(request, "Item removed from cart.", "info")
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")

    return RedirectResponse(url=str(request.url_for("cart_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/checkout", response_class=HTMLResponse, name="checkout_page")
def checkout_page(request: Request, current_user: OptionalCurrentUser, db: DBSession) -> Response:
    guard = _guard_page_user(request, current_user, Role.USER)
    if isinstance(guard, Response):
        return guard

    cart = user_service.get_active_cart(db, user_id=guard.id)
    if not cart.items:
        flash(request, "Add items to your cart before checking out.", "warning")
        return RedirectResponse(url=str(request.url_for("cart_page")), status_code=status.HTTP_303_SEE_OTHER)

    dashboard_data = dashboard_service.get_user_dashboard_data(db, guard)
    return _render(
        request,
        "checkout.html",
        current_user=guard,
        cart=cart,
        active_membership=dashboard_data["active_membership"],
    )


@router.post("/checkout", name="checkout_submit")
def checkout_submit(
    request: Request,
    current_user: OptionalCurrentUser,
    db: DBSession,
    delivery_address: str = Form(...),
    notes: str = Form(""),
    payment_method: str = Form("simulation"),
) -> Response:
    guard = _guard_page_user(request, current_user, Role.USER)
    if isinstance(guard, Response):
        return guard

    try:
        order = order_service.checkout_cart(
            db,
            user=guard,
            payload=CheckoutRequest(
                delivery_address=delivery_address,
                notes=notes or None,
                payment_method=payment_method,
            ),
        )
        flash(request, f"Order {order.order_number} was created successfully.", "success")
        return RedirectResponse(
            url=str(request.url_for("success_page", order_id=order.id)),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")
        return RedirectResponse(url=str(request.url_for("checkout_page")), status_code=status.HTTP_303_SEE_OTHER)


@router.get("/success/{order_id}", response_class=HTMLResponse, name="success_page")
def success_page(
    request: Request,
    order_id: int,
    current_user: OptionalCurrentUser,
    db: DBSession,
) -> Response:
    guard = _guard_page_user(request, current_user, Role.USER)
    if isinstance(guard, Response):
        return guard

    order = order_service.get_user_order(db, user_id=guard.id, order_id=order_id)
    return _render(request, "success.html", current_user=guard, order=order)


@router.post("/success/{order_id}/pay", name="success_payment_submit")
def success_payment_submit(
    request: Request,
    order_id: int,
    current_user: OptionalCurrentUser,
    db: DBSession,
    succeed: bool = Form(True),
    provider_message: str = Form(""),
) -> Response:
    guard = _guard_page_user(request, current_user, Role.USER)
    if isinstance(guard, Response):
        return guard

    try:
        order_service.simulate_payment(
            db,
            user=guard,
            order_id=order_id,
            payload=PaymentSimulationRequest(
                succeed=succeed,
                provider_message=provider_message or None,
            ),
        )
        flash(request, "Payment simulation completed.", "success")
    except Exception as exc:
        flash(request, _message_from_exception(exc), "danger")

    return RedirectResponse(
        url=str(request.url_for("success_page", order_id=order_id)),
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _render(
    request: Request,
    template_name: str,
    *,
    current_user: User | None,
    status_code: int = status.HTTP_200_OK,
    **context,
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            **context,
            "current_user": current_user,
            "csrf_token": get_or_create_csrf_token(request),
            "flash_messages": pop_flashes(request),
        },
        status_code=status_code,
    )


def _guard_page_user(
    request: Request,
    current_user: User | None,
    *roles: Role,
) -> User | RedirectResponse:
    if current_user is None:
        flash(request, "Please log in to continue.", "warning")
        return RedirectResponse(url=str(request.url_for("login_page")), status_code=status.HTTP_303_SEE_OTHER)

    if roles and current_user.role not in roles:
        flash(request, "That page is not available for your account.", "warning")
        return RedirectResponse(
            url=_dashboard_path(request, current_user.role),
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return current_user


def _dashboard_path(request: Request, role: Role) -> str:
    route_name_map = {
        Role.ADMIN: "admin_dashboard_page",
        Role.VENDOR: "vendor_dashboard_page",
        Role.USER: "user_dashboard_page",
    }
    return str(request.url_for(route_name_map[role]))


def _safe_local_path(request: Request, candidate: str, fallback_route_name: str) -> str:
    stripped_candidate = (candidate or "").strip()
    if stripped_candidate.startswith("/"):
        parsed = urlsplit(stripped_candidate)
        if not parsed.scheme and not parsed.netloc:
            return stripped_candidate
    return str(request.url_for(fallback_route_name))


def _active_categories(db: DBSession) -> list[Category]:
    return list(
        db.execute(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.name.asc())
        )
        .scalars()
        .all()
    )


def _optional_int(raw_value: str) -> int | None:
    stripped = raw_value.strip()
    return int(stripped) if stripped else None


def _message_from_exception(exc: Exception) -> str:
    if hasattr(exc, "detail"):
        detail = getattr(exc, "detail")
        if isinstance(detail, str):
            return detail
        return str(detail)
    if isinstance(exc, ValidationError):
        first_error = exc.errors()[0] if exc.errors() else None
        if first_error:
            return str(first_error.get("msg", "Invalid form submission."))
    if isinstance(exc, ValueError):
        return str(exc)
    return "Something went wrong. Please try again."


def _status_from_exception(exc: Exception) -> int:
    if hasattr(exc, "status_code"):
        return int(getattr(exc, "status_code"))
    return status.HTTP_400_BAD_REQUEST
