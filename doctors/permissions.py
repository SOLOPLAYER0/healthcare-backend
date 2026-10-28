from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsCreatorOrReadOnly(BasePermission):
    """Any authenticated user may read; only the creator may change or delete."""

    message = "You do not have permission to modify this doctor record."

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.created_by_id is not None and obj.created_by_id == request.user.id
