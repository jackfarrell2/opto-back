from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import UserSerializer
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model, authenticate
import re
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta


User = get_user_model()


@api_view(['POST'])
def login(request):
    email = request.data.get('email', '')
    password = request.data.get('password', '')

    user = authenticate(request, email=email, password=password)

    if user is not None:
        if not user.is_confirmed:
            return Response({'detail': 'Please confirm your email before logging in'}, status=status.HTTP_400_BAD_REQUEST)
        token, created = Token.objects.get_or_create(user=user)
        serializer = UserSerializer(instance=user)
        serializer_data = serializer.data
        serializer_data['isStaff'] = user.is_staff
        return Response({'token': token.key, 'user': {'user': True, 'isStaff': serializer_data['isStaff']}})
    else:
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def resend_code(request):
    try:
        user = User.objects.get(email=request.data.get('email', ''))
        email = user.email
        new_confirmation_code = get_random_string(length=8)
        user.password_reset_code = new_confirmation_code
        user.password_reset_code_created_at = timezone.now()
        user.save()
        subject = 'Password reset request'
        body = f'Hi {user.first_name},\n\nWe received a request to reset your password. Use the confirmation code below to reset your password.\n\nConfirmation code: {new_confirmation_code}\n\nIf you did not request a password reset, please ignore this email or contact us at support@dfsopto.com.\n\nBest,\nDFS Opto Team'
        send_mail(
            subject,
            body,
            'no-reply@dfsopto.com',
            [email],
            fail_silently=False,
        )
        return Response({'detail': 'Password reset email sent'}, status=status.HTTP_200_OK)
    except:
        return Response({'detail': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def resend_confirmation(request):
    try:
        user = User.objects.get(email=request.data.get('email', ''))
        if user.is_confirmed:
            return Response({'detail': 'User already confirmed'}, status=status.HTTP_400_BAD_REQUEST)
        email = user.email
        new_confirmation_code = get_random_string(length=64)
        user.confirmation_code = new_confirmation_code
        user.confirmation_code_created_at = timezone.now()
        user.save()
        subject = 'Welcome to DFS Opto! Confirm your email!'
        body = f'Hi {user.first_name},\n\nThank you for signing up with DFS Opto! You\'re just one step away from completing your registration and accessing all the features available to you.\n\nTo activate your account, please click the link below:\n\nhttps://dfsopto.com/activate/{new_confirmation_code}\n\nThis link will confirm your email address and activate your account. If you did not sign up for DFS Opto, please ignore this email or contact us at support@dfsopto.com if you feel this is an error.\n\nBest regards,\nDFS Opto Team'
        send_mail(
            subject,
            body,
            'no-reply@dfsopto.com',  # From email
            [email],  # To email
            fail_silently=False,
        )
        return Response({'detail': 'Confirmation email sent'}, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({'detail': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@authentication_classes([TokenAuthentication])
def reset_password(request):
    try:
        user = request.user
        new_password = request.data.get('newPassword', '')
        confirmed_password = request.data.get('confirmedPassword', '')
        if new_password != confirmed_password:
            return Response({'detail': 'Passwords do not match'}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_password) < 8:
            return Response({'detail': 'Password must be at least 8 characters long'}, status=status.HTTP_400_BAD_REQUEST)
        if not re.search("[a-z]", new_password):
            return Response({'detail': 'Password must contain at least one lowercase letter'}, status=status.HTTP_400_BAD_REQUEST)
        if not re.search("[A-Z]", new_password):
            return Response({'detail': 'Password must contain at least one uppercase letter'}, status=status.HTTP_400_BAD_REQUEST)
        if not re.search("[0-9]", new_password):
            return Response({'detail': 'Password must contain at least one number'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({'detail': 'Password reset successfully'}, status=status.HTTP_200_OK)
    except:
        return Response({'detail': 'There was an error resetting your password'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def reset_password_request(request):
    try:
        user = User.objects.get(email=request.data.get('email', ''))
        email = user.email
        new_password_code = get_random_string(length=8)
        user.password_reset_code = new_password_code
        user.password_reset_code_created_at = timezone.now()
        user.save()
        subject = 'Password reset request'
        body = f'Hi {user.first_name},\n\nWe received a request to reset your password. Use the confirmation code below to reset your password.\n\nConfirmation code: {new_password_code}\n\nIf you did not request a password reset, please ignore this email or contact us at support@dfsopto.com.\n\nBest,\nDFS Opto Team'
        send_mail(
            subject,
            body,
            'no-reply@dfsopto.com',
            [email],
            fail_silently=False,
        )
        return Response({'detail': 'Password reset email sent'}, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({'detail': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def signup(request):
    serializer = UserSerializer(data=request.data)

    if serializer.is_valid():
        # Extracting data
        first_name = request.data.get('firstName', '')
        last_name = request.data.get('lastName', '')
        email = request.data.get('email', '')
        password = request.data.get('password', '')

        # Validate password
        if len(password) < 8:
            return Response({"error": "Password must be at least 8 characters long."}, status=status.HTTP_400_BAD_REQUEST)

        if not re.search("[a-z]", password):
            return Response({"error": "Password must contain at least one lowercase letter."}, status=status.HTTP_400_BAD_REQUEST)

        if not re.search("[A-Z]", password):
            return Response({"error": "Password must contain at least one uppercase letter."}, status=status.HTTP_400_BAD_REQUEST)

        if not re.search("[0-9]", password):
            return Response({"error": "Password must contain at least one number."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate Email
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return Response({"error": "Invalid email."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate Names
        if first_name == '' or last_name == '':
            return Response({"error": "First and last name are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Generate confirmation code
        confirmation_code = get_random_string(length=64)
        confirmation_code_created_at = timezone.now()

        # Creating the user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_confirmed=False,
            confirmation_code=confirmation_code,
            confirmation_code_created_at=confirmation_code_created_at
        )

        # Create email info
        subject = 'Welcome to DFS Opto! Confirm your email!'
        body = f'Hi {user.first_name},\n\nThank you for signing up with DFS Opto! You\'re just one step away from completing your registration and accessing all the features available to you.\n\nTo activate your account, please click the link below:\n\nhttps://dfsopto.com/activate/{confirmation_code}\n\nThis link will confirm your email address and activate your account. If you did not sign up for DFS Opto, please ignore this email or contact us at support@dfsopto.com if you feel this is an error.\n\nBest,\nDFS Opto Team'

        # Send email
        send_mail(
            subject,
            body,
            'no-reply@dfsopto.com',  # From email
            [email],  # To email
            fail_silently=False,
        )

        # Creating and returning the authentication token
        token = Token.objects.create(user=user)
        serializer = UserSerializer(instance=user)
        serializer_data = serializer.data
        serializer_data['isStaff'] = user.is_staff
        return Response({'token': token.key, 'user': {'user': True, 'isStaff': serializer_data['isStaff']}}, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def confirm_email(request, token):
    user = get_object_or_404(User, confirmation_code=token)
    if user.confirmation_code_created_at:
        time_elapsed = timezone.now() - user.confirmation_code_created_at
        if time_elapsed > timedelta(hours=24):
            return Response({'detail': 'Confirmation code expired'}, status=status.HTTP_400_BAD_REQUEST)
    user.is_confirmed = True
    user.confirmation_code = ''
    user.confirmation_code_created_at = None
    user.save()
    token, created = Token.objects.get_or_create(user=user)
    serializer = UserSerializer(instance=user)
    serializer_data = serializer.data
    serializer_data['isStaff'] = user.is_staff
    return Response({'token': token.key, 'user': {'user': True, 'isStaff': serializer_data['isStaff']}}, status=status.HTTP_200_OK)


@api_view(['GET'])
def confirm_password_reset(request, token):
    try:
        user = get_object_or_404(User, password_reset_code=token)
        if user.password_reset_code_created_at:
            time_elapsed = timezone.now() - user.password_reset_code_created_at
            if time_elapsed > timedelta(hours=24):
                return Response({'detail': 'Code expired, please try again'}, status=status.HTTP_400_BAD_REQUEST)
        user.password_reset_code = ''
        user.password_reset_code_created_at = None
        user.save()
        token, created = Token.objects.get_or_create(user=user)
        serializer = UserSerializer(instance=user)
        serializer_data = serializer.data
        serializer_data['isStaff'] = user.is_staff
        return Response({'token': token.key, 'user': {'user': True, 'isStaff': serializer_data['isStaff']}}, status=status.HTTP_200_OK)
    except:
        return Response({'detail': 'Invalid code, please try again'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def test_token(request):
    return Response({})
