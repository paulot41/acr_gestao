from functools import wraps

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm

class CustomLoginView(LoginView):
    """Vista personalizada de login com suporte a multi-entidade."""
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        """Redirecionar após login bem-sucedido."""
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse('dashboard_router')

    def form_valid(self, form):
        """Processar login válido com informação da entidade."""
        entity = self.request.POST.get('entity', 'acr')
        remember_me = self.request.POST.get('remember_me')

        # Configurar duração da sessão
        if remember_me:
            self.request.session.set_expiry(1209600)  # 2 semanas
        else:
            self.request.session.set_expiry(0)  # Até fechar o browser

        # Armazenar entidade preferida na sessão
        self.request.session['preferred_entity'] = entity

        messages.success(
            self.request,
            f'Bem-vindo ao ACR Gestão! Entidade: {"ACR Ginásio" if entity == "acr" else "Proform Wellness"}'
        )

        return super().form_valid(form)

    def form_invalid(self, form):
        """Processar login inválido com mensagem personalizada."""
        messages.error(
            self.request,
            'Credenciais inválidas. Por favor, verifique o seu nome de utilizador e palavra-passe.'
        )
        return super().form_invalid(form)

class CustomLogoutView(LogoutView):
    """Vista personalizada de logout."""
    template_name = 'registration/logout.html'

    def dispatch(self, request, *args, **kwargs):
        """Processar logout com mensagem de confirmação."""
        if request.user.is_authenticated:
            messages.success(request, 'Sessão terminada com sucesso. Até à próxima!')
        return super().dispatch(request, *args, **kwargs)

@login_required
def profile_view(request):
    """Vista do perfil do utilizador."""
    context = {
        'user': request.user,
        'preferred_entity': request.session.get('preferred_entity', 'acr'),
        'session_info': {
            'last_login': request.user.last_login,
            'is_staff': request.user.is_staff,
            'is_superuser': request.user.is_superuser,
        }
    }
    return render(request, 'registration/profile.html', context)

def check_user_permissions(user, required_permission=None, allowed_roles=None):
    """Verificar permissões e papéis do utilizador."""
    if not user.is_authenticated:
        return False

    if allowed_roles and get_user_role(user) not in allowed_roles:
        return False

    if required_permission and not user.has_perm(required_permission):
        return False

    return True

def get_user_role(user):
    """Determinar o papel do utilizador no sistema."""
    if not user.is_authenticated:
        return None

    # Preferir informação do UserProfile se existir
    profile = getattr(user, "profile", None)
    if profile:
        return profile.user_type

    if user.is_superuser:
        return "admin"
    if user.is_staff:
        return "staff"
    if user.groups.filter(name="Instrutores").exists():
        return "instructor"
    if user.groups.filter(name="Rececionistas").exists():
        return "staff"
    return "client"


def role_required(allowed_roles):
    """Decorator para restringir acesso com base no papel do utilizador."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if get_user_role(request.user) in allowed_roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return login_required(_wrapped_view)

    return decorator

class UserRoleMiddleware:
    """Middleware para determinar e armazenar o papel do utilizador."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user_role = get_user_role(request.user)
            request.preferred_entity = request.session.get('preferred_entity', 'acr')
        else:
            request.user_role = None
            request.preferred_entity = 'acr'

        response = self.get_response(request)
        return response

# Função de view para compatibilidade com URLs existentes
def login_view(request):
    """Vista de login como função para compatibilidade."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo, {user.first_name or user.username}!')
                return redirect('dashboard_router')
            else:
                messages.error(request, 'Credenciais inválidas.')
        else:
            messages.error(request, 'Por favor, corrija os erros abaixo.')
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    """Vista de logout."""
    logout(request)
    messages.success(request, 'Logout realizado com sucesso.')
    return redirect('login')
