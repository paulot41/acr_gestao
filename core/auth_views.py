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
from django.conf import settings

class CustomLoginView(LoginView):
    """Vista personalizada de login com suporte a multi-entidade."""
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        """Redirecionar após login bem-sucedido."""
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse('core:dashboard_router')

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
    if user.groups.filter(name="Direção ACR").exists():
        return "acr_direction"
    if user.groups.filter(name="Staff ACR").exists():
        return "acr_staff"
    if user.groups.filter(name="Direção Técnica Proform").exists():
        return "proform_director"
    if user.groups.filter(name="Staff Proform").exists():
        return "proform_staff"
    if user.groups.filter(name="Instrutores").exists():
        return "instructor"
    if user.is_staff or user.groups.filter(name="Rececionistas").exists():
        return "staff"
    return "client"


def role_required(allowed_roles):
    """Decorator para restringir acesso com base no papel do utilizador."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            user_role = get_user_role(request.user)
            profile = getattr(request.user, "profile", None)

            # Verificação direta
            if user_role in allowed_roles:
                return view_func(request, *args, **kwargs)

            # Hierarquia: se 'staff' for permitido, todos os sub-papéis de staff têm acesso geral
            staff_roles = {"staff", "acr_direction", "acr_staff", "proform_director", "proform_staff"}
            if "staff" in allowed_roles:
                if user_role in staff_roles or request.user.is_staff:
                    return view_func(request, *args, **kwargs)

            # Se 'instructor' for permitido, proform_director também tem acesso de instrutor
            if "instructor" in allowed_roles:
                if user_role in {"instructor", "proform_director"} or (profile and profile.instructor):
                    return view_func(request, *args, **kwargs)

            raise PermissionDenied

        return login_required(_wrapped_view)

    return decorator


def acr_required(require_direction=False):
    """
    Decorator para restringir acesso a utilizadores da Associação ACR.
    Utilizadores do ProForm não afiliados à ACR recebem PermissionDenied (403).
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, "profile", None)
            if profile:
                if require_direction and not profile.can_manage_association:
                    raise PermissionDenied("Acesso reservado aos membros da Direção da Associação ACR.")
                if not profile.is_acr:
                    raise PermissionDenied("Acesso reservado aos membros afiliados à Associação ACR.")
                return view_func(request, *args, **kwargs)

            # Verificação alternativa via grupos Django
            is_dir = request.user.groups.filter(name="Direção ACR").exists()
            is_staff_acr = request.user.groups.filter(name="Staff ACR").exists()
            if require_direction and is_dir:
                return view_func(request, *args, **kwargs)
            if not require_direction and (is_dir or is_staff_acr):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied("Acesso reservado à Associação ACR.")

        return login_required(_wrapped_view)

    return decorator


def proform_required(require_director=False):
    """
    Decorator para restringir acesso a utilizadores afiliados ao ProForm.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, "profile", None)
            if profile:
                if require_director and not profile.is_proform_director:
                    raise PermissionDenied("Acesso reservado à Direção Técnica do ProForm.")
                if not profile.is_proform:
                    raise PermissionDenied("Acesso reservado a elementos do ProForm.")
                return view_func(request, *args, **kwargs)

            is_pf_dir = request.user.groups.filter(name="Direção Técnica Proform").exists()
            is_pf_staff = request.user.groups.filter(name__in=["Staff Proform", "Instrutores"]).exists()
            if require_director and is_pf_dir:
                return view_func(request, *args, **kwargs)
            if not require_director and (is_pf_dir or is_pf_staff):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied("Acesso reservado à equipa ProForm.")

        return login_required(_wrapped_view)

    return decorator


def protocol_access_required(require_approval_power=False):
    """
    Decorator para supervisão do Protocolo ACR & Proform SC.
    Permite consulta à Direção ACR e à Direção Técnica ProForm.
    A aprovação formal exige poder de aprovação estatutário (Direção ACR / Admin).
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, "profile", None)
            if profile:
                if require_approval_power and not profile.can_approve_protocol:
                    raise PermissionDenied("Apenas a Direção da Associação ACR pode aprovar o fecho financeiro do protocolo.")
                if not profile.can_supervise_protocol:
                    raise PermissionDenied("Sem permissões de supervisão do protocolo.")
                return view_func(request, *args, **kwargs)

            is_dir_acr = request.user.groups.filter(name="Direção ACR").exists()
            is_dir_pf = request.user.groups.filter(name="Direção Técnica Proform").exists()
            if require_approval_power and is_dir_acr:
                return view_func(request, *args, **kwargs)
            if not require_approval_power and (is_dir_acr or is_dir_pf):
                return view_func(request, *args, **kwargs)

            raise PermissionDenied("Sem autorização para aceder à supervisão do protocolo.")

        return login_required(_wrapped_view)

    return decorator


class UserRoleMiddleware:
    """Middleware para determinar e armazenar o papel e permissões detalhadas do utilizador."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            request.user_role = get_user_role(request.user)
            request.user_profile = getattr(request.user, "profile", None)
            request.preferred_entity = request.session.get('preferred_entity', 'acr')

            # Permissões booleanas convenientes para templates e views
            if request.user.is_superuser:
                request.is_management = True
                request.is_acr = True
                request.is_proform = True
                request.is_acr_direction = True
                request.is_proform_director = True
                request.can_manage_association = True
                request.can_manage_sports = True
                request.can_supervise_protocol = True
                request.can_approve_protocol = True
                request.user_role_display = "Administrador Global"
            elif request.user_profile:
                p = request.user_profile
                request.is_management = p.can_access_admin()
                request.is_acr = p.is_acr
                request.is_proform = p.is_proform
                request.is_acr_direction = p.is_acr_direction
                request.is_proform_director = p.is_proform_director
                request.can_manage_association = p.can_manage_association
                request.can_manage_sports = p.can_manage_sports
                request.can_supervise_protocol = p.can_supervise_protocol
                request.can_approve_protocol = p.can_approve_protocol
                request.user_role_display = p.get_user_type_display()
            else:
                user_groups = set(request.user.groups.values_list('name', flat=True))
                request.is_management = request.user.is_staff or bool(user_groups)
                request.is_acr = bool(user_groups.intersection({"Direção ACR", "Staff ACR"}))
                request.is_proform = bool(user_groups.intersection({"Direção Técnica Proform", "Staff Proform", "Instrutores"}))
                request.is_acr_direction = "Direção ACR" in user_groups
                request.is_proform_director = "Direção Técnica Proform" in user_groups
                request.can_manage_association = "Direção ACR" in user_groups or "Staff ACR" in user_groups
                request.can_manage_sports = bool(user_groups.intersection({"Direção Técnica Proform", "Staff Proform", "Instrutores", "Direção ACR"}))
                request.can_supervise_protocol = bool(user_groups.intersection({"Direção ACR", "Direção Técnica Proform"}))
                request.can_approve_protocol = "Direção ACR" in user_groups
                request.user_role_display = request.user_role or "Utilizador"
        else:
            request.user_role = None
            request.user_profile = None
            request.preferred_entity = 'acr'
            request.is_management = False
            request.is_acr = False
            request.is_proform = False
            request.is_acr_direction = False
            request.is_proform_director = False
            request.can_manage_association = False
            request.can_manage_sports = False
            request.can_supervise_protocol = False
            request.can_approve_protocol = False
            request.user_role_display = ""

        response = self.get_response(request)
        return response


# Funções simples de autenticação
def login_view(request):
    """Renderiza e processa o formulário de login."""
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, 'auth/login.html', {'form': form})

@login_required
def logout_view(request):
    """Termina a sessão do utilizador."""
    logout(request)
    return render(request, 'auth/logout.html')
