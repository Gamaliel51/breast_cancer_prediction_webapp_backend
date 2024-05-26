import os
import random
import string
import pickle
import environ
import pandas as pd
from sklearn.svm import SVC
from sklearn.datasets import load_breast_cancer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from rest_framework import status
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from mainapp.serializer import ChangePasswordSerializer


env = environ.Env()
environ.Env.read_env()


def generate_random_string(length):
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for _ in range(length))


def send_password_mail(email, password):
    try:
        app_email = env('APP_EMAIL')
        app_email_password = env('APP_EMAIL_PASSWORD')

        msg = MIMEMultipart()
        msg['From'] = app_email
        msg['To'] = email
        msg['Subject'] = "Password Change"

        body = f"You requested a password change.\nYour new password is {password}"
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(app_email, app_email_password)
        text = msg.as_string()
        server.sendmail(app_email, email, text)
        server.quit()

        return True
    except Exception as E:
        print(E)
        return False


class TestView(APIView):

    def get(self, request):
        data = {'user': request.user}
        print(request.user)
        return Response(str(data))


class UpdatePassword(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            old_password = serializer.validated_data.get('old_password')
            new_password = serializer.validated_data.get('new_password')
            confirm_password = serializer.validated_data.get('confirm_password')

            user = request.user
            if not check_password(old_password, user.password):
                return Response({'detail': 'Old password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)

            if new_password != confirm_password:
                return Response({'detail': 'New passwords do not match.'}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()
            return Response({'detail': 'Password updated successfully.'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@permission_classes([AllowAny])
@authentication_classes([])
class ForgotPassword(APIView):

    def post(self, request):
        user = request.data.get('username')
        if not user:
            return Response({'error': 'Username is required'}, status=400)

        try:
            user = User.objects.get(username=user)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)

        new_password = generate_random_string(random.randint(1, 20))
        user.set_password(new_password)
        user.save()

        active = send_password_mail(user.email, new_password)
        if active:
            return Response({'message': 'Check your email for your new password'}, status=200)

        return Response({'message': 'An error occurred'}, status=500)


@permission_classes([AllowAny])
@authentication_classes([])
class SignUp(APIView):

    def post(self, request):
        data = request.POST
        print(data)
        username = data['username']
        password = data['password']
        email = data['email']

        user = User.objects.create_user(username=username, password=password, email=email)

        if user:
            return Response('ok')

        return Response('fail')


class ModelPredict(APIView):

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self):
        dataset = load_breast_cancer()
        df = pd.DataFrame(dataset.data, columns=dataset.feature_names)

        df['target'] = dataset.target

        X = df[dataset.feature_names].copy()
        y = df['target']

        scale = StandardScaler()
        X_scaled = scale.fit_transform(X)

        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, train_size=.8, random_state=3)

        model = SVC()
        model.fit(X_train, y_train)

        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

        with open(os.path.join(__location__, 'svm_model.pickle'), 'wb') as f:
            pickle.dump(model, f)

        return Response('ok')


    def post(self, request):
        df = pd.DataFrame(request.data, index=[0])

        scaler = StandardScaler()
        data = scaler.fit_transform(df)

        __location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

        pickle_in = open(os.path.join(__location__, 'svm_model.pickle'), "rb")
        model = pickle.load(pickle_in)

        svm_predict = model.predict(data)

        if svm_predict[0] == 0:
            result = 'Benign'
        else:
            result = 'Malignant'

        return Response({'result': result})

