import os, requests

def login(request):
    auth = request.authorization
    if not auth:
        return None, ("Missing authorization", 401)
    
    basicAuth = (auth.username, auth.password)
    response = requests.post(
        f"http://{os.environ.get('AUTH_SVC_ADDRESS')}/login",
        auth=basicAuth
    )
    
    if response.status_code == 200:
        return response.text, None
    else:
        return None, (response.text, response.status_code)

def signup(request):
    try:
        # Get form data instead of JSON
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            return None, ("Missing email or password", 400)
        
        data = {
            "email": email,
            "password": password
        }
        
        response = requests.post(
            f"http://{os.environ.get('AUTH_SVC_ADDRESS')}/signup",
            json=data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 201:
            return "user created successfully", None
        else:
            return None, (response.text, response.status_code)
            
    except Exception as e:
        return None, ("Internal server error", 500)