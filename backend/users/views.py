# users/views.py
from rest_framework import generics, permissions

from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    """
    Public registration endpoint. Creates a new user with a securely
    hashed password via User.objects.create_user().
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]