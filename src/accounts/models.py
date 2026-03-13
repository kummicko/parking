from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom user model that inherits all fields from AbstractUser.

    This is the recommended starting point for a new Django project
    as it allows for easy extension of the user model later.
    """

    # ⚠️ These fields are necessary to fix reverse accessor clashes
    # when replacing the default User model. DO NOT REMOVE THEM.
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="accounts_user_groups",  # Use your app_name_user_groups
        blank=True,
        help_text="The groups this user belongs to.",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="accounts_user_permissions",  # Use your app_name_user_permissions
        blank=True,
        help_text="Specific permissions for this user.",
        related_query_name="user",
    )

    def __str__(self):
        return self.username or self.email or "Unnamed User"


# Your custom fields (like telephone) would go here if you needed them.
# Currently, this model is a mirror of the default User model.
