from django.urls import path
from . import views

urlpatterns = [
    path("", views.quiz_app, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.user_login, name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("quiz/", views.quiz_page, name="quiz"),
    path("api/get-quiz/", views.get_quiz, name="get_quiz"),
    path("api/save-result/", views.save_result, name="save_result"),
    path("api/generate-questions/", views.generate_questions, name="generate_questions"),
    path("scores/", views.my_scores, name="scores"),
    path("profile/", views.profile, name="profile"),
]
