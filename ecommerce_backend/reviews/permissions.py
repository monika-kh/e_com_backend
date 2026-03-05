from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsReviewOwnerOrReadOnly(BasePermission):
  """
  Allow read-only access for everyone, but write access only to the review owner.
  """

  def has_object_permission(self, request, view, obj) -> bool:
      if request.method in SAFE_METHODS:
          return True
      return getattr(obj, "user_id", None) == getattr(request.user, "id", None)

