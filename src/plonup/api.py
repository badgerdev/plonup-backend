from ninja_extra import NinjaExtraAPI
from moderation.api import ModerationController
from notifications.api import NotificationController
from users.api import UserController, RegisterController, ReviewController, AuthController
from announcements.api import AnnouncementController
from ninja_jwt.controller import NinjaJWTDefaultController
from users.account_api import AccountController

print("🔥 api.py został załadowany i działa!")
api_v1 = NinjaExtraAPI(version="v1")  # version 1 of API!


api_v1.register_controllers(
    UserController,
    NinjaJWTDefaultController,
    AnnouncementController,
    RegisterController,
    ReviewController,
    ModerationController,
    NotificationController,
    AuthController,
    AccountController,
)
