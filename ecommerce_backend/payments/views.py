import json
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from decimal import Decimal

from orders.models import Order
from payments.models import Payment
from payments.serializers import RazorpayCreateOrderSerializer, RazorpayVerifySerializer
from payments.services.payment_service import RazorpayService
from cart.models import Cart


def set_payment_status(payment, payment_status, payment_id=None, signature=None):
    update_fields = ["payment_status"]
    payment.payment_status = payment_status

    if payment_id:
        payment.razorpay_payment_id = payment_id
        update_fields.append("razorpay_payment_id")
    if signature:
        payment.razorpay_signature = signature
        update_fields.append("razorpay_signature")

    payment.save(update_fields=update_fields)

    order = payment.order_id
    if payment_status == "success":
        order.status = "paid"
        order.save(update_fields=["status"])
        try:
            Cart.objects.get(user=order.user).items.all().delete()
        except Cart.DoesNotExist:
            pass


class RazorpayCreateOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RazorpayCreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = get_object_or_404(
            Order,
            id=serializer.validated_data["order_id"],
            user=request.user,
        )

        if order.status != "pending":
            return Response(
                {"error": f"Payment cannot be started for a {order.status} order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        service = RazorpayService()
        payment = Payment.objects.filter(order_id=order).first()
        if payment:
            if payment.payment_status == "success":
                return Response(
                    {"error": "Payment already completed for this order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if payment.payment_status == "failed":
                payment.payment_status = "pending"
                payment.save(update_fields=["payment_status"])

            # The order-creation endpoint already made this Razorpay order. Reuse
            # it when the client needs the checkout details again.
            return Response(
                {
                    "order_id": order.id,
                    "razorpay_order_id": payment.razorpay_order_id,
                    "amount": int(Decimal(order.total_amount) * 100),
                    "currency": "INR",
                    "key": service.key_id,
                    "payment_status": payment.payment_status,
                },
                status=status.HTTP_200_OK,
            )

        rp_order = service.create_order(
            amount=order.total_amount,
            receipt=order.order_number,
            currency="INR",
        )

        payment = Payment.objects.create(
            order_id=order,
            payment_method="razorpay",
            razorpay_order_id=rp_order["id"],
            payment_status="pending",
        )

        return Response(
            {
                "order_id": order.id,
                "razorpay_order_id": payment.razorpay_order_id,
                "amount": rp_order["amount"],
                "currency": rp_order.get("currency", "INR"),
                "key": service.key_id,
                "payment_status": payment.payment_status,
            },
            status=status.HTTP_200_OK,
        )


class RazorpayVerifyPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RazorpayVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            order = get_object_or_404(
                Order.objects.select_for_update(),
                id=serializer.validated_data["order_id"],
                user=request.user,
            )
            payment = get_object_or_404(Payment.objects.select_for_update(), order_id=order)

            # Idempotency: if already paid, return success
            if order.status == "paid" and payment.payment_status == "success":
                return Response(
                    {"message": "Payment already verified.", "status": "success"},
                    status=status.HTTP_200_OK,
                )

            if order.status != "pending":
                return Response(
                    {"error": f"Payment cannot be verified for a {order.status} order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if payment.razorpay_order_id != serializer.validated_data["razorpay_order_id"]:
                return Response({"error": "Razorpay order does not match this payment."}, status=status.HTTP_400_BAD_REQUEST)

            service = RazorpayService()
            ok = service.verify_signature(
                razorpay_order_id=serializer.validated_data["razorpay_order_id"],
                razorpay_payment_id=serializer.validated_data["razorpay_payment_id"],
                razorpay_signature=serializer.validated_data["razorpay_signature"],
            )

            if ok:
                set_payment_status(
                    payment,
                    "success",
                    payment_id=serializer.validated_data["razorpay_payment_id"],
                    signature=serializer.validated_data["razorpay_signature"],
                )

                return Response(
                    {"message": "Payment verified.", "status": "success"},
                    status=status.HTTP_200_OK,
                )

            set_payment_status(
                payment,
                "failed",
                payment_id=serializer.validated_data["razorpay_payment_id"],
                signature=serializer.validated_data["razorpay_signature"],
            )

            return Response(
                {"message": "Invalid payment signature.", "status": "failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RazorpayWebhookAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        signature = request.headers.get("X-Razorpay-Signature", "")
        if not RazorpayService.verify_webhook_signature(
            body=request.body, signature=signature
        ):
            return Response({"error": "Invalid webhook signature."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = json.loads(request.body)
            payment_data = event["payload"]["payment"]["entity"]
            razorpay_order_id = payment_data["order_id"]
        except (json.JSONDecodeError, KeyError, TypeError):
            return Response({"error": "Invalid webhook payload."}, status=status.HTTP_400_BAD_REQUEST)

        event_name = event.get("event")
        if event_name not in {"payment.captured", "payment.failed"}:
            return Response(status=status.HTTP_204_NO_CONTENT)

        with transaction.atomic():
            payment_reference = get_object_or_404(
                Payment.objects.only("order_id_id"),
                razorpay_order_id=razorpay_order_id,
            )
            Order.objects.select_for_update().get(id=payment_reference.order_id_id)
            payment = Payment.objects.select_for_update().get(
                id=payment_reference.id
            )
            if event_name == "payment.failed" and payment.payment_status == "success":
                return Response(status=status.HTTP_200_OK)

            set_payment_status(
                payment,
                "success" if event_name == "payment.captured" else "failed",
                payment_id=payment_data.get("id"),
            )

        return Response(status=status.HTTP_200_OK)
