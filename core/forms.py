from django import forms
from django.core.exceptions import ValidationError
from .models import Person, Instructor, Modality, Event, Resource, ClassGroup


class PersonForm(forms.ModelForm):
    """Formulário para criação/edição de clientes."""

    class Meta:
        model = Person
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'nif',
            'date_of_birth', 'address', 'emergency_contact',
            'entity_affiliation', 'status', 'notes', 'photo'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apelido'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+351 912 345 678'}),
            'nif': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NIF (opcional)'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Morada completa'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contacto de emergência'}),
            'entity_affiliation': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notas adicionais...'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Verificar se já existe outro cliente com este email na mesma organização
            existing = Person.objects.filter(email=email)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError('Já existe um cliente com este email.')
        return email

    def clean_nif(self):
        nif = self.cleaned_data.get('nif')
        if nif:
            # Validação básica do NIF português
            if len(nif) != 9 or not nif.isdigit():
                raise ValidationError('NIF deve ter 9 dígitos.')
        return nif


class InstructorForm(forms.ModelForm):
    """Formulário para criação/edição de instrutores."""

    class Meta:
        model = Instructor
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'specialties',
            'entity_affiliation', 'acr_commission_rate', 'proform_commission_rate',
            'is_active', 'photo'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apelido'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+351 912 345 678'}),
            'specialties': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Especialidades e certificações...'}),
            'entity_affiliation': forms.Select(attrs={'class': 'form-select'}),
            'acr_commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'proform_commission_rate': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            existing = Instructor.objects.filter(email=email)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError('Já existe um instrutor com este email.')
        return email


class ModalityForm(forms.ModelForm):
    """Formulário para criação/edição de modalidades."""

    class Meta:
        model = Modality
        fields = [
            'name', 'description', 'entity_type', 'default_duration_minutes',
            'max_capacity', 'color', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da modalidade'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição detalhada...'}),
            'entity_type': forms.Select(attrs={'class': 'form-select'}),
            'default_duration_minutes': forms.NumberInput(attrs={'class': 'form-control', 'min': '15', 'max': '240', 'step': '15'}),
            'max_capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '100'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ClassGroupForm(forms.ModelForm):
    """Formulário para criação/edição de turmas."""

    class Meta:
        model = ClassGroup
        fields = [
            'name', 'description', 'modality', 'instructor',
            'max_students', 'level', 'start_date', 'end_date',
            'members', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da turma'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição da turma...'}),
            'modality': forms.Select(attrs={'class': 'form-select'}),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
            'max_students': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '50'}),
            'level': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ex: Iniciante, Intermédio, Avançado'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'members': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '10'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

        if organization:
            self.fields['modality'].queryset = Modality.objects.filter(organization=organization, is_active=True)
            self.fields['instructor'].queryset = Instructor.objects.filter(organization=organization, is_active=True)
            self.fields['members'].queryset = Person.objects.filter(organization=organization, status='active')


class EventForm(forms.ModelForm):
    """Formulário para criação/edição de eventos."""

    class Meta:
        model = Event
        fields = [
            'title', 'description', 'event_type', 'resource', 'modality',
            'instructor', 'class_group', 'individual_client',
            'starts_at', 'ends_at', 'capacity'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título do evento'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição...'}),
            'event_type': forms.Select(attrs={'class': 'form-select'}),
            'resource': forms.Select(attrs={'class': 'form-select'}),
            'modality': forms.Select(attrs={'class': 'form-select'}),
            'instructor': forms.Select(attrs={'class': 'form-select'}),
            'class_group': forms.Select(attrs={'class': 'form-select'}),
            'individual_client': forms.Select(attrs={'class': 'form-select'}),
            'starts_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'ends_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '100'}),
        }

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

        if organization:
            self.fields['resource'].queryset = Resource.objects.filter(organization=organization, is_available=True)
            self.fields['modality'].queryset = Modality.objects.filter(organization=organization, is_active=True)
            self.fields['instructor'].queryset = Instructor.objects.filter(organization=organization, is_active=True)
            self.fields['class_group'].queryset = ClassGroup.objects.filter(organization=organization, is_active=True)
            self.fields['individual_client'].queryset = Person.objects.filter(organization=organization, status='active')

        # Campos opcionais
        self.fields['modality'].required = False
        self.fields['instructor'].required = False
        self.fields['class_group'].required = False
        self.fields['individual_client'].required = False

    def clean(self):
        cleaned_data = super().clean()
        event_type = cleaned_data.get('event_type')
        class_group = cleaned_data.get('class_group')
        individual_client = cleaned_data.get('individual_client')
        capacity = cleaned_data.get('capacity')
        starts_at = cleaned_data.get('starts_at')
        ends_at = cleaned_data.get('ends_at')

        # Validar horários
        if starts_at and ends_at:
            if ends_at <= starts_at:
                raise ValidationError('A hora de fim deve ser posterior à hora de início.')

        # Validar tipo de evento
        if event_type == Event.EventType.GROUP_CLASS:
            if not class_group:
                raise ValidationError('Aulas de turma devem ter uma turma associada.')
            if capacity and capacity > class_group.max_students:
                cleaned_data['capacity'] = class_group.max_students

        elif event_type == Event.EventType.INDIVIDUAL:
            if not individual_client:
                raise ValidationError('Aulas individuais devem ter um cliente associado.')
            cleaned_data['capacity'] = 1

        return cleaned_data


class ResourceForm(forms.ModelForm):
    """Formulário para criação/edição de recursos/espaços."""

    class Meta:
        model = Resource
        fields = [
            'name', 'description', 'entity_type', 'capacity',
            'is_available', 'equipment_list', 'special_features'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do espaço'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição do espaço...'}),
            'entity_type': forms.Select(attrs={'class': 'form-select'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '200'}),
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'equipment_list': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Lista de equipamentos disponíveis...'}),
            'special_features': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Características especiais...'}),
        }


# Formulário de filtros para listas
class ClientFilterForm(forms.Form):
    """Formulário de filtros para lista de clientes."""

    ENTITY_CHOICES = [
        ('', 'Todas as entidades'),
        ('acr_only', 'Apenas ACR'),
        ('proform_only', 'Apenas Proform'),
        ('both', 'ACR + Proform'),
    ]

    STATUS_CHOICES = [
        ('', 'Todos os estados'),
        ('active', 'Ativo'),
        ('inactive', 'Inativo'),
        ('suspended', 'Suspenso'),
    ]

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pesquisar por nome, email ou telefone...'
        })
    )

    entity_affiliation = forms.ChoiceField(
        choices=ENTITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class EventFilterForm(forms.Form):
    """Formulário de filtros para eventos."""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pesquisar eventos...'
        })
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    def __init__(self, *args, **kwargs):
        organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

        if organization:
            self.fields['resource'] = forms.ModelChoiceField(
                queryset=Resource.objects.filter(organization=organization),
                required=False,
                widget=forms.Select(attrs={'class': 'form-select'})
            )

            self.fields['instructor'] = forms.ModelChoiceField(
                queryset=Instructor.objects.filter(organization=organization, is_active=True),
                required=False,
                widget=forms.Select(attrs={'class': 'form-select'})
            )
