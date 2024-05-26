from django.urls import path
import mainapp.views


urlpatterns = [
    path("test/", mainapp.views.TestView.as_view()),
    path("signup/", mainapp.views.SignUp.as_view()),
    path("changepassword/", mainapp.views.UpdatePassword.as_view()),
    path("forgotpassword/", mainapp.views.ForgotPassword.as_view()),
    path("predict/", mainapp.views.ModelPredict.as_view())
]