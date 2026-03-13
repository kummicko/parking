from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from .forms import LoginForm
from django.conf import settings  # Needed for LOGIN_REDIRECT_URL
from django.contrib.auth.decorators import login_not_required


@login_not_required
def user_login(request):
    """
    Handles user authentication.
    - GET: Displays the login form.
    - POST: Validates credentials and logs the user in.
    """
    # If the user is already logged in, redirect them away
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        # Pass request into the form constructor (required by AuthenticationForm)
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            # form.get_user() retrieves the authenticated user object
            user = form.get_user()
            login(request, user)

            # Redirect logic, prioritizing the 'next' URL parameter/post data
            next_url = request.POST.get("next") or settings.LOGIN_REDIRECT_URL
            return redirect(next_url)
    else:
        # GET request: Display a new, empty form
        form = LoginForm()

    # Note the template path: 'accounts/login.html'
    return render(request, "accounts/login.html", {"form": form})


@login_not_required
def user_logout(request):
    """
    Logs out the user and redirects them to the LOGOUT_REDIRECT_URL defined in settings.
    """
    # Use Django's built-in function to clear the session
    logout(request)
    # The redirection target is defined by LOGOUT_REDIRECT_URL in settings.py, which you set to 'login'.
    # We can redirect manually to ensure immediate action, though Django often handles this automatically.
    return redirect(settings.LOGOUT_REDIRECT_URL)
