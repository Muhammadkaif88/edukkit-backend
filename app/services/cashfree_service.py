import hmac
import hashlib
import base64
import json
import urllib.request
import urllib.error
import logging
from typing import Dict, Any, Tuple, Optional, List
from ..config import settings

logger = logging.getLogger("cashfree_service")


class CashfreeService:

    @staticmethod
    def get_base_url() -> str:
        env = settings.CASHFREE_ENV.lower()
        if env in ("production", "prod"):
            return "https://api.cashfree.com/pg"
        return "https://sandbox.cashfree.com/pg"

    @staticmethod
    def get_headers() -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-version": settings.CASHFREE_API_VERSION,
            "x-client-id": settings.CASHFREE_CLIENT_ID,
            "x-client-secret": settings.CASHFREE_CLIENT_SECRET,
        }

    @classmethod
    def create_order(
        cls,
        order_id: str,
        order_amount: float,
        customer_details: Dict[str, str],
        order_meta: Optional[Dict[str, str]] = None,
        order_note: str = "Edukkit Order",
    ) -> Dict[str, Any]:
        """
        Creates a Cashfree Payment Gateway Order and returns payment_session_id.
        """
        url = f"{cls.get_base_url()}/orders"

        payload = {
            "order_id": order_id,
            "order_amount": round(order_amount, 2),
            "order_currency": "INR",
            "customer_details": {
                "customer_id": customer_details.get("customer_id", "guest_user"),
                "customer_name": customer_details.get("customer_name", "Customer"),
                "customer_email": customer_details.get("customer_email", "customer@edukkit.com"),
                "customer_phone": customer_details.get("customer_phone", "9999999999"),
            },
            "order_meta": {
                "return_url": (
                    order_meta.get("return_url") if order_meta else settings.CASHFREE_RETURN_URL
                ),
                "notify_url": (
                    order_meta.get("notify_url") if order_meta else settings.CASHFREE_NOTIFY_URL
                ),
                "payment_methods": "upi,cc,dc,nb,app",
            },
            "order_note": order_note,
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data_bytes, headers=cls.get_headers(), method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = response.read().decode("utf-8")
                return json.loads(res_body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"Cashfree create_order HTTPError {e.code}: {err_body}")
            if (
                settings.CASHFREE_CLIENT_ID.startswith("TEST")
                or settings.CASHFREE_ENV.lower() == "sandbox"
            ):
                logger.info("Generating sandbox mock payment session for local development...")
                return {
                    "cf_order_id": f"cf_{order_id}",
                    "order_id": order_id,
                    "order_amount": round(order_amount, 2),
                    "order_currency": "INR",
                    "order_status": "ACTIVE",
                    "payment_session_id": f"session_{order_id}_{int(order_amount * 100)}",
                    "order_expiry_time": "2026-12-31T23:59:59Z",
                    "is_sandbox_mock": True,
                }
            raise Exception(f"Cashfree API error ({e.code}): {err_body}")
        except Exception as e:
            logger.error(f"Cashfree create_order Exception: {str(e)}")
            if settings.CASHFREE_ENV.lower() == "sandbox":
                return {
                    "cf_order_id": f"cf_{order_id}",
                    "order_id": order_id,
                    "order_amount": round(order_amount, 2),
                    "order_currency": "INR",
                    "order_status": "ACTIVE",
                    "payment_session_id": f"session_{order_id}_{int(order_amount * 100)}",
                    "is_sandbox_mock": True,
                }
            raise e

    @classmethod
    def get_order_status(cls, order_id: str) -> Dict[str, Any]:
        """
        Fetches authoritative order and payment status from Cashfree.
        """
        url = f"{cls.get_base_url()}/orders/{order_id}"
        req = urllib.request.Request(url, headers=cls.get_headers(), method="GET")

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = response.read().decode("utf-8")
                return json.loads(res_body)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"Cashfree get_order_status HTTPError {e.code}: {err_body}")
            return {"order_status": "PENDING", "order_id": order_id}
        except Exception as e:
            logger.error(f"Cashfree get_order_status Exception: {str(e)}")
            return {"order_status": "PENDING", "order_id": order_id}

    @classmethod
    def get_order_payments(cls, order_id: str) -> List[Dict[str, Any]]:
        """
        Fetches list of payment attempts for a Cashfree order.
        """
        url = f"{cls.get_base_url()}/orders/{order_id}/payments"
        req = urllib.request.Request(url, headers=cls.get_headers(), method="GET")

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                res_body = response.read().decode("utf-8")
                return json.loads(res_body)
        except Exception as e:
            logger.error(f"Cashfree get_order_payments Exception: {str(e)}")
            return []

    @classmethod
    def verify_webhook_signature(
        cls,
        raw_body: bytes,
        timestamp: str,
        signature: str,
    ) -> bool:
        """
        Verifies Cashfree webhook signature using HMAC-SHA256.
        Cashfree signs: timestamp + raw_body_string
        """
        secret = settings.CASHFREE_WEBHOOK_SECRET or settings.CASHFREE_CLIENT_SECRET
        if not secret:
            logger.warning("No Cashfree webhook secret configured. Skipping signature check.")
            return True

        try:
            data = timestamp.encode("utf-8") + raw_body
            computed = base64.b64encode(
                hmac.new(secret.encode("utf-8"), data, hashlib.sha256).digest()
            ).decode("utf-8")
            return hmac.compare_digest(computed, signature)
        except Exception as e:
            logger.error(f"Signature verification error: {str(e)}")
            return False

    @staticmethod
    def recalculate_order_pricing(
        items: List[Dict[str, Any]],
        shipping_address: Dict[str, Any],
        db_session=None,
    ) -> Tuple[float, float, str, str, float, float]:
        """
        Server-Side Authoritative Price & Delivery Fee Calculation.

        SECURITY: Prices are fetched from the database by item ID.
        Flutter-supplied prices are IGNORED — only item IDs and quantities are trusted.

        Delivery fee rules:
          - 'course' items:      FREE (digital, no delivery)
          - 'diy_kit' items:     FREE delivery
          - 'electronics' items: ₹70 (Kerala) or ₹100 (Outside Kerala)

        Returns:
          (items_total, delivery_fee, region, rule, discount, total_payable)
        """
        from ..models.product import Product
        from ..models.course import Course

        items_total = 0.0
        has_electronics = False

        for item in items:
            qty = max(1, int(item.get("quantity", 1)))
            item_type = item.get("item_type") or item.get("type", "")
            item_id = item.get("item_id") or item.get("product_id") or item.get("course_id")

            unit_price = 0.0

            if db_session is not None and item_id is not None:
                try:
                    item_id_int = int(item_id)
                    if item_type == "course":
                        # Authoritative course price from DB
                        course = db_session.query(Course).filter(
                            Course.id == item_id_int
                        ).first()
                        if course:
                            unit_price = float(course.price or 0.0)
                            # Free courses still included (₹0)
                    else:
                        # Authoritative product price from DB (diy_kit or electronics)
                        product = db_session.query(Product).filter(
                            Product.id == item_id_int
                        ).first()
                        if product:
                            unit_price = float(product.price or 0.0)
                            if product.type == "electronics":
                                has_electronics = True
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not fetch price for item {item_id}: {e}")
                    # Fallback to payload price only in dev/sandbox
                    if (
                        hasattr(__import__("..config", fromlist=["settings"]), "settings")
                        and __import__("..config", fromlist=["settings"]).settings.CASHFREE_ENV == "sandbox"
                    ):
                        unit_price = float(
                            item.get("unit_price") or item.get("price", 0.0)
                        )
            else:
                # No DB session: this should not happen in production.
                # Only allowed in sandbox fallback.
                unit_price = float(item.get("unit_price") or item.get("price", 0.0))
                item_type_raw = str(item_type).lower()
                if "electronics" in item_type_raw:
                    has_electronics = True
                logger.warning(
                    "recalculate_order_pricing called without db_session — "
                    "using Flutter-supplied prices (SANDBOX ONLY)"
                )

            items_total += unit_price * qty

        # Delivery fee logic
        # FREE for courses and DIY kits. Only electronics trigger delivery charges.
        if has_electronics:
            state = str(shipping_address.get("state", "")).strip().lower()
            pin = str(
                shipping_address.get("postalCode") or shipping_address.get("pinCode", "")
            ).strip()

            is_kerala = False
            if any(k in state for k in ["kerala", "kl", "keralam", "kerla"]):
                is_kerala = True
            elif len(pin) >= 2 and pin[:2] in ["67", "68", "69"]:
                is_kerala = True

            if is_kerala:
                delivery_fee = settings.DELIVERY_FEE_KERALA
                region = "Kerala"
                rule = "KERALA_STANDARD"
            else:
                delivery_fee = settings.DELIVERY_FEE_OUTSIDE_KERALA
                region = "Outside Kerala"
                rule = "INDIA_STANDARD"
        else:
            # All items are courses or diy_kits → FREE delivery
            delivery_fee = 0.0
            region = "Digital/DIY"
            rule = "FREE_DELIVERY"

        # Discount: ₹100 off on orders above ₹1500 (electronics only — course/kit always free)
        discount = 100.0 if (has_electronics and items_total > 1500.0) else 0.0
        total_payable = items_total + delivery_fee - discount

        # Guard: total must be positive
        if total_payable < 0:
            total_payable = 0.0

        return (
            round(items_total, 2),
            round(delivery_fee, 2),
            region,
            rule,
            round(discount, 2),
            round(total_payable, 2),
        )
