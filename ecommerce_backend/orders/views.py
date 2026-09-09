from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from uuid import uuid4

from cart.models import Cart
from users.models import Address
from orders.models import Order, OrderItem
from orders.serializers import PlaceOrderSerializer
from payments.models import Payment
from payments.services.payment_service import RazorpayService


class PlaceOrderAPIView(APIView):
    """
    Create an order from the current user's cart and selected address.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        address_id = serializer.validated_data["address_id"]

        address = get_object_or_404(Address, id=address_id, user=request.user)

        try:
            cart = Cart.objects.prefetch_related("items__product").get(user=request.user)
        except Cart.DoesNotExist:
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = list(cart.items.all())
        if not cart_items:
            return Response({"error": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        unavailable_item = next(
            (item for item in cart_items if not item.product or not item.product.is_active),
            None,
        )
        if unavailable_item:
            return Response(
                {"error": "A product in your cart is no longer available."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        total_amount = sum(item.product.price * item.quantity for item in cart_items)
        order_number = f"ORD-{uuid4().hex.upper()}"
        shipping_snapshot = (
            f"{address.full_name}\n"
            f"{address.address_line}\n"
            f"{address.city}, {address.state} - {address.pincode}\n"
            f"Phone: {address.phone}"
        )

        with transaction.atomic():
            service = RazorpayService()
            razorpay_order = service.create_order(
                amount=total_amount,
                receipt=order_number,
                currency="INR",
            )

            order = Order.objects.create(
                user=request.user,
                order_number=order_number,
                shipping_address_text=shipping_snapshot,
                total_amount=total_amount,
                status="pending",
            )

            payment = Payment.objects.create(
                order_id=order,
                payment_method="razorpay",
                razorpay_order_id=razorpay_order["id"],
                payment_status="pending",
            )

            OrderItem.objects.bulk_create(
                [
                    OrderItem(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price,
                    )
                    for item in cart_items
                ]
            )

        return Response(
            {
                "order_id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": order.total_amount,
                "shipping_address_text": order.shipping_address_text,
                "payment": {
                    "payment_method": payment.payment_method,
                    "payment_status": payment.payment_status,
                    "razorpay_order_id": payment.razorpay_order_id,
                    "amount": razorpay_order["amount"],
                    "currency": razorpay_order.get("currency", "INR"),
                    "key": service.key_id,
                },
                "created_at": order.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class UserOrdersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        orders = (
            Order.objects.filter(user=request.user)
            .select_related("payment")
            .prefetch_related("items")
            .annotate(total_quantity=Sum("items__quantity"))
            .order_by("-created_at")
        )

        data = [
            {
                "order_id": order.id,
                "order_number": order.order_number,
                "delivery_status": order.status,
                "total_amount": order.total_amount,
                "total_quantity": int(order.total_quantity or 0),
                "payment_method": getattr(getattr(order, "payment", None), "payment_method", None),
                "payment_status": getattr(getattr(order, "payment", None), "payment_status", "pending"),
                "created_at": order.created_at,
            }
            for order in orders
        ]

        return Response(data, status=status.HTTP_200_OK)


class OrderDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects.select_related("payment").prefetch_related("items__product"),
            id=order_id,
            user=request.user,
        )
        items = order.items.all()
        payment = getattr(order, "payment", None)
        data = {
                "order_id": order.id,
                "order_number": order.order_number,
                "delivery_status": order.status,
                "payment_method": getattr(payment, "payment_method", None),
                "payment_status": getattr(payment, "payment_status", "pending"),
                "total_amount": order.total_amount,
                "total_quantity": sum(i.quantity for i in items),
                "created_at": order.created_at,
                "address": {
                    "snapshot": order.shipping_address_text,
                },
                "items": [
                    {
                        "product_id": item.product.id if item.product else None,
                        "product_name": item.product.name if item.product else None,
                        "product_slug": item.product.slug if item.product else None,
                        "quantity": item.quantity,
                        "price": item.price,
                    }
                    for item in items
                ],
            }
        return Response(data, status=status.HTTP_200_OK)
