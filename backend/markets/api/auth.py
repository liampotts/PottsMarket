import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def login_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'balance': float(user.userprofile.balance),
                'is_staff': user.is_staff or user.is_superuser,
            })
        else:
            return JsonResponse({'error': 'Invalid credentials'}, status=401)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

@csrf_exempt
def logout_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    logout(request)
    return JsonResponse({'status': 'logged out'})

@csrf_exempt
def signup_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        email = data.get('email', '')
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already taken'}, status=400)
            
        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user) # Auto login after signup
        
        return JsonResponse({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff or user.is_superuser,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def me_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
        
    return JsonResponse({
        'id': request.user.id,
        'username': request.user.username,
        'email': request.user.email,
        'balance': float(request.user.userprofile.balance),
        'is_staff': request.user.is_staff or request.user.is_superuser,
    })
