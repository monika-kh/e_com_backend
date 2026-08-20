from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from orders.models import Order
from payments.models import Payment
from payments.serializers import RazorpayCreateOrderSerializer, RazorpayVerifySerializer
from payments.services.payment_service import RazorpayService
from cart.models import Cart


class RazorpayCreateOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = RazorpayCreateOrderSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            order = get_object_or_404(
                Order,
                id=serializer.validated_data["order_id"],
                user=request.user,
            )

            if order.status == "paid":
                return Response(
                    {"error": "Order is already paid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payment, _ = Payment.objects.get_or_create(
                order=order,
                defaults={
                    "payment_method": "razorpay",
                    "amount": order.total_amount,
                    "status": "pending",
                },
            )

            if payment.status == "success":
                return Response(
                    {"error": "Payment already completed for this order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            service = RazorpayService()
            rp_order = service.create_order(
                amount=order.total_amount,
                receipt=f"order_{order.id}",
                currency="INR",
            )

            return Response(
                {
                    "razorpay_order_id": rp_order.get("id"),
                    "amount": rp_order.get("amount"),
                    "currency": rp_order.get("currency", "INR"),
                    "key": service.key_id,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RazorpayVerifyPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = RazorpayVerifySerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            order = get_object_or_404(
                Order,
                id=serializer.validated_data["order_id"],
                user=request.user,
            )

            payment, _ = Payment.objects.get_or_create(
                order=order,
                defaults={
                    "payment_method": "razorpay",
                    "amount": order.total_amount,
                    "status": "pending",
                },
            )

            # Idempotency: if already paid, return success
            if order.status == "paid" and payment.status == "success":
                return Response(
                    {"message": "Payment already verified.", "status": "success"},
                    status=status.HTTP_200_OK,
                )

            if order.status == "paid":
                return Response(
                    {"error": "Order is already paid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            service = RazorpayService()
            ok = service.verify_signature(
                razorpay_order_id=serializer.validated_data["razorpay_order_id"],
                razorpay_payment_id=serializer.validated_data["razorpay_payment_id"],
                razorpay_signature=serializer.validated_data["razorpay_signature"],
            )

            if ok:
                payment.payment_method = "razorpay"
                payment.transaction_id = serializer.validated_data["razorpay_payment_id"]
                payment.amount = order.total_amount
                payment.status = "success"
                payment.save()

                order.status = "paid"
                order.save(update_fields=["status"])

                # Clear the user's cart only after payment success
                try:
                    cart = Cart.objects.get(user=request.user)
                    cart.items.all().delete()
                except Cart.DoesNotExist:
                    pass

                return Response(
                    {"message": "Payment verified.", "status": "success"},
                    status=status.HTTP_200_OK,
                )

            payment.payment_method = "razorpay"
            payment.transaction_id = serializer.validated_data["razorpay_payment_id"]
            payment.amount = order.total_amount
            payment.status = "failed"
            payment.save()

            return Response(
                {"message": "Invalid payment signature.", "status": "failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
