from django import forms
from django.forms import ModelForm
from .models import Person, Instructor, Modality, Event, Resource, Organization


class PersonForm(ModelForm):
    """Formulário para criar/editar clientes com suporte multi-entidade."""

    class Meta:
        model = Person
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'nif',
            'date_of_birth', 'address', 'emergency_contact',
            'photo', 'status', 'entity_affiliation', 'notes'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apelido'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+351 912 345 678'}),
            'nif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123456789'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Morada completa'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contacto de emergência'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'entity_affiliation': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notas adicionais...'}),
        }


class InstructorForm(ModelForm):
    """Formulário para criar/editar instrutores com suporte multi-entidade."""

    class Meta:
        model = Instructor
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'specialties', 'photo', 'is_active', 'entity_affiliation',
            'acr_commission_rate', 'proform_commission_rate'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apelido'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+351 912 345 678'}),
            'specialties': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Especialidades (Pilates, Musculação, etc.)'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'entity_affiliation': forms.Select(attrs={'class': 'form-select'}),
            'acr_commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
            'proform_commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'step': 0.01}),
        }


class ModalityForm(ModelForm):
    """Formulário para criar/editar modalidades com suporte multi-entidade."""

    class Meta:
        model = Modality
        fields = [
            'name', 'description', 'default_duration_minutes',
            'max_capacity', 'color', 'is_active', 'entity_type',
            'price_per_class'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da modalidade'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição da modalidade...'}),
            'default_duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': 15, 'max': 180}),
            'max_capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 50}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'entity_type': forms.Select(attrs={'class': 'form-select'}),
            'price_per_class': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
        }


class OrganizationSettingsForm(ModelForm):
    """Formulário para configurações da organização."""

    class Meta:
        model = Organization
        fields = [
            'name', 'org_type', 'gym_monthly_fee', 'wellness_monthly_fee'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'org_type': forms.Select(attrs={'class': 'form-select'}),
            'gym_monthly_fee': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
            'wellness_monthly_fee': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
        }


class EventForm(ModelForm):
    """Formulário para criar/editar eventos/aulas."""

    class Meta:
        model = Event
        fields = ['resource', 'title', 'starts_at', 'ends_at', 'capacity']
        widgets = {
            'resource': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título da aula'}),
            'starts_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'ends_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 50}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resource'].empty_label = "Selecione um espaço"


class QuickBookingForm(forms.Form):
    """Formulário rápido para reservas no Gantt."""
    client = forms.ModelChoiceField(
        queryset=Person.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Selecione um cliente"
    )

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Person.objects.filter(
            organization=organization,
            status='active'
        ).order_by('first_name')


class GanttFilterForm(forms.Form):
    """Formulário de filtros para a vista Gantt."""
    resource = forms.ModelChoiceField(
        queryset=Resource.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Todos os espaços"
    )
    instructor = forms.ModelChoiceField(
        queryset=Instructor.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Todos os instrutores"
    )
    modality = forms.ModelChoiceField(
        queryset=Modality.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Todas as modalidades"
    )

    def __init__(self, organization, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resource'].queryset = Resource.objects.filter(organization=organization)
        self.fields['instructor'].queryset = Instructor.objects.filter(organization=organization, is_active=True)
        self.fields['modality'].queryset = Modality.objects.filter(organization=organization, is_active=True)
