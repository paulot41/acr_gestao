from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.utils import timezone


# -----------------
# Multi-entidade (ACR + Ginásio)
# -----------------
class Organization(models.Model):
    name = models.CharField(max_length=120, unique=True)
    domain = models.CharField(
        max_length=120,
        unique=True,
        help_text="Domínio principal para scoping (ex.: acr.local, gym.local)",
    )
    logo = models.ImageField(upload_to="branding/", null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


# ----------------
# Pessoas e Perfis
# ----------------
GENDER = [("M", "Masculino"), ("F", "Feminino"), ("O", "Outro")]


class Person(models.Model):
    # Identidade global (sem FK para Organization).
    nome = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    nif = models.CharField(max_length=15, blank=True)
    morada = models.CharField(max_length=255, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    genero = models.CharField(max_length=1, choices=GENDER, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome

    @property
    def is_minor(self) -> bool:
        if not self.data_nascimento:
            return False
        return (timezone.now().date() - self.data_nascimento).days < 18 * 365


class OrgMembership(models.Model):
    """Liga uma Person a uma Organization com um ‘perfil’/funções locais."""
    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    roles = models.JSONField(default=list)  # ["ATHLETE"], ["GYMCLIENT"], ["INSTRUCTOR"], etc.
    numero_socio = models.CharField(max_length=30, blank=True)  # se aplicável ao ginásio

    class Meta:
        unique_together = ("person", "organization")

    def __str__(self) -> str:
        return f"{self.person} @ {self.organization}"


class Guardian(models.Model):
    """Enc. de educação/contacto para menores (por organização)."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="guardians")
    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    relacao = models.CharField(max_length=50, blank=True, help_text="Ex.: Pai, Mãe, Tio...")

    class Meta:
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class Athlete(models.Model):
    """Perfil de atleta (ACR)."""
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name="athlete")
    guardian = models.ForeignKey(Guardian, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notas = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.person.nome


class GymClient(models.Model):
    """Perfil de cliente do ginásio."""
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name="gymclient")
    numero_socio = models.CharField(max_length=30, blank=True)

    def __str__(self) -> str:
        return self.person.nome


class Instructor(models.Model):
    """Instrutor/treinador (pode ter user associado)."""
    person = models.OneToOneField(Person, on_delete=models.CASCADE, related_name="instructor")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    ativo = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"Instrutor {self.person.nome}"


# -----------
# Inscrições / Modalidades
# ------------
class Modality(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="modalities")
    nome = models.CharField(max_length=100)

    class Meta:
        unique_together = ("organization", "nome")
        ordering = ["organization__name", "nome"]

    def __str__(self) -> str:
        return f"{self.nome} ({self.organization.name})"


class Enrollment(models.Model):
    """Inscrição de uma person numa modalidade de uma organização/época."""
    ESTADOS = [("A", "Ativa"), ("I", "Inativa")]

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="enrollments")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="enrollments")
    modality = models.ForeignKey(Modality, on_delete=models.PROTECT, related_name="enrollments")
    epoca = models.CharField(max_length=9)  # "2025/2026"
    estado = models.CharField(max_length=1, choices=ESTADOS, default="A")

    class Meta:
        unique_together = ("person", "organization", "modality", "epoca")
        ordering = ["-epoca", "organization__name", "modality__nome", "person__nome"]

    def __str__(self) -> str:
        return f"{self.person} - {self.modality} [{self.epoca}]"


# -------
# Faturação por organização
# -------
class Account(models.Model):
    """Conta financeira da Person dentro de uma Organization (cobrança local)."""
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="accounts")
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="accounts")

    class Meta:
        unique_together = ("person", "organization")

    def __str__(self) -> str:
        return f"Conta de {self.person} @ {self.organization.name}"


PRODUCT_KINDS = [
    ("QUOTA", "Quota/Propina"),
    ("SEGURO", "Seguro desportivo"),
    ("LICENCA", "Licença/Federação"),
    ("MENSALIDADE", "Mensalidade Ginásio"),
    ("AULA", "Aula/Pacote"),
    ("OUTRO", "Outro"),
]


class Product(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=15, choices=PRODUCT_KINDS)

    class Meta:
        unique_together = ("organization", "name")
        ordering = ["organization__name", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.organization.name})"


class Price(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="prices")
    active_from = models.DateField()
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["-active_from"]

    def __str__(self) -> str:
        return f"{self.product} @ {self.active_from}: {self.amount}€"


# --------
# Descontos
# --------
class DiscountRule(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="discount_rules")
    name = models.CharField(max_length=120)
    # Condições simples (podemos evoluir depois):
    requires_dual_org = models.BooleanField(default=False)  # inscrito na org atual E noutra
    percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # ex.: 10.00 = 10%

    class Meta:
        ordering = ["organization__name", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.organization.name})"


# -----------
# Pricing helper
# -----------
def compute_price(account: Account, product: Product) -> Decimal:
    """Calcula o preço aplicando regras de desconto simples."""
    latest_price = product.prices.order_by("-active_from").first()
    if latest_price is None:
        # Sem preço definido — poderíamos lançar exceção conforme regra de negócio
        return Decimal("0.00")

    base = latest_price.amount

    # condição “duas organizações” (tem também membership noutra org?)
    has_other_org = OrgMembership.objects.filter(
        person=account.person
    ).exclude(organization=account.organization).exists()

    discount_total = Decimal("0.00")
    for rule in DiscountRule.objects.filter(organization=account.organization):
        if rule.requires_dual_org and has_other_org:
            discount_total += (base * (rule.percent / Decimal("100")))

    final = (base - discount_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if final < Decimal("0.00"):
        final = Decimal("0.00")
    return final
