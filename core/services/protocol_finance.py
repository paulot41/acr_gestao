"""
Motor de cálculo financeiro da partilha de receitas do Protocolo ACR & Proform SC.
Implementa o cálculo automático e estrito da divisão tripartida:
Receita Bruta = Remuneração Instrutores + Parcela Ginásio Proform SC + Parcela Associação ACR.
"""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any

from django.db.models import Sum, Count, Q
from django.utils import timezone

from core.models import (
    Organization, Person, Instructor, Modality, Event, Booking,
    Payment, InstructorCommission, ProtocolPeriodSettlement
)


def calculate_period_protocol_split(
    organization: Organization,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    Calcula a divisão tripartida da receita do protocolo no período selecionado:
    1. Receita Bruta Arrecadada (Caixa, Mensalidades, Créditos)
    2. Remuneração devida a cada Instrutor pelas aulas lecionadas
    3. Parcela líquida do Ginásio Proform SC (instalações, espaço, receção)
    4. Parcela líquida da Associação ACR (promoção cultural/desportiva, seguros, supervisão)
    """
    # 1. Pagamentos recebidos no período
    payments = Payment.objects.filter(
        organization=organization,
        paid_date__gte=start_date,
        paid_date__lte=end_date,
        status=Payment.Status.COMPLETED
    ).select_related('person')

    gross_revenue = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Segmentação da receita bruta por afiliação do praticante
    acr_only_revenue = payments.filter(
        person__entity_affiliation=Person.EntityAffiliation.ACR_ONLY
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    proform_only_revenue = payments.filter(
        person__entity_affiliation=Person.EntityAffiliation.PROFORM_ONLY
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    joint_revenue = payments.filter(
        person__entity_affiliation=Person.EntityAffiliation.BOTH
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # 2. Aulas lecionadas pelos instrutores no período
    events_in_period = Event.objects.filter(
        organization=organization,
        starts_at__date__gte=start_date,
        starts_at__date__lte=end_date
    ).select_related('instructor', 'modality', 'resource')

    instructors_breakdown = []
    instructors_total_payout = Decimal('0.00')

    active_instructors = Instructor.objects.filter(
        organization=organization, is_active=True
    ).order_by('first_name', 'last_name')

    total_classes_period = events_in_period.count()

    for inst in active_instructors:
        inst_events = events_in_period.filter(instructor=inst)
        classes_count = inst_events.count()
        if classes_count == 0:
            continue

        # Presenças reais no tapete
        attendances_count = Booking.objects.filter(
            event__in=inst_events,
            status=Booking.Status.CHECKED_IN
        ).count()

        # Determinar taxa de comissão padrão do instrutor
        # Se for majoritariamente ACR usa acr_commission_rate, senão proform_commission_rate
        inst_affiliation = inst.entity_affiliation
        if inst_affiliation == Instructor.EntityAffiliation.ACR_ONLY:
            rate = Decimal(str(inst.acr_commission_rate or 60.00))
        elif inst_affiliation == Instructor.EntityAffiliation.PROFORM_ONLY:
            rate = Decimal(str(inst.proform_commission_rate or 70.00))
        else:
            rate = Decimal(str(inst.acr_commission_rate or 60.00))

        # Calcular valor gerado ou devido pelas aulas do instrutor
        # Verificar se existem InstructorCommission já registadas
        commissions_qs = InstructorCommission.objects.filter(
            instructor=inst,
            event__in=inst_events
        )
        if commissions_qs.exists():
            amount_due = commissions_qs.aggregate(total=Sum('instructor_amount'))['total'] or Decimal('0.00')
            is_settled = not commissions_qs.filter(is_paid=False).exists()
        else:
            # Estimativa proporcional da receita da aula baseada nas presenças ou distribuição proporcional
            if total_classes_period > 0 and gross_revenue > Decimal('0.00'):
                # Parcela da receita correspondente ao volume de aulas do instrutor
                class_share = (gross_revenue * Decimal(classes_count)) / Decimal(total_classes_period)
                amount_due = (class_share * rate) / Decimal('100.00')
            else:
                amount_due = Decimal('0.00')
            is_settled = False

        amount_due = amount_due.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        instructors_total_payout += amount_due

        instructors_breakdown.append({
            'instructor': inst,
            'classes_count': classes_count,
            'attendances_count': attendances_count,
            'commission_rate': rate,
            'amount_due': amount_due,
            'is_settled': is_settled,
        })

    # Limitar o total de instrutores para não ultrapassar a receita bruta total
    if gross_revenue > Decimal('0.00') and instructors_total_payout > gross_revenue:
        instructors_total_payout = gross_revenue

    # 3. Divisão da Margem Institucional (Ginásio Proform SC vs Associação ACR)
    net_entity_margin = max(Decimal('0.00'), gross_revenue - instructors_total_payout)

    # Regra do Protocolo:
    # A margem líquida divide-se proporcionalmente às fontes de receita
    if gross_revenue > Decimal('0.00'):
        # Quota da ACR: margem sobre acr_only + 50% da margem sobre receitas conjuntas
        acr_ratio = (acr_only_revenue + (joint_revenue / Decimal('2.0'))) / gross_revenue
        acr_share = (net_entity_margin * acr_ratio).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        acr_share = Decimal('0.00')

    # Garantir integridade aritmética estrita (sem arredondamentos perdidos):
    # gross_revenue = instructors_total_payout + proform_share + acr_share
    proform_share = max(Decimal('0.00'), net_entity_margin - acr_share)

    # 4. Detalhe por Modalidade / Arte Marcial
    modalities = Modality.objects.filter(organization=organization).order_by('name')
    modality_breakdown = []
    for mod in modalities:
        mod_events = events_in_period.filter(modality=mod)
        mod_classes = mod_events.count()
        mod_attendances = Booking.objects.filter(
            event__in=mod_events,
            status=Booking.Status.CHECKED_IN
        ).count()

        modality_breakdown.append({
            'modality': mod,
            'classes_count': mod_classes,
            'attendances_count': mod_attendances,
            'entity_type': mod.get_entity_type_display(),
        })

    # 5. Parâmetros Contratuais da Configuração Dinâmica
    config = getattr(organization, 'get_protocol_config', None)
    protocol_config = config() if config else None

    active_athletes_count = Person.objects.filter(
        organization=organization, status=Person.Status.ACTIVE
    ).count()

    admin_fee_rate = protocol_config.acr_admin_fee_per_athlete if protocol_config else Decimal('1.00')
    contractual_acr_admin = (Decimal(active_athletes_count) * admin_fee_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    annual_insurance = protocol_config.insurance_annual_premium if protocol_config else Decimal('362.82')
    monthly_insurance_share = (annual_insurance / Decimal('12.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    return {
        'start_date': start_date,
        'end_date': end_date,
        'gross_revenue': gross_revenue,
        'acr_only_revenue': acr_only_revenue,
        'proform_only_revenue': proform_only_revenue,
        'joint_revenue': joint_revenue,
        'instructors_total': instructors_total_payout,
        'instructors_breakdown': instructors_breakdown,
        'net_entity_margin': net_entity_margin,
        'proform_share': proform_share,
        'acr_share': acr_share,
        'modality_breakdown': modality_breakdown,
        'total_payments_count': payments.count(),
        'total_classes_period': total_classes_period,
        'protocol_config': protocol_config,
        'active_athletes_count': active_athletes_count,
        'contractual_acr_admin': contractual_acr_admin,
        'monthly_insurance_share': monthly_insurance_share,
    }


def create_or_update_period_settlement(
    organization: Organization,
    start_date: date,
    end_date: date,
    notes: str = ""
) -> ProtocolPeriodSettlement:
    """
    Cria ou atualiza um fecho de contas oficial do protocolo para o período indicado.
    """
    split_data = calculate_period_protocol_split(organization, start_date, end_date)

    settlement, created = ProtocolPeriodSettlement.objects.get_or_create(
        organization=organization,
        period_start=start_date,
        period_end=end_date,
        defaults={
            'title': f"Fecho Protocolo ({start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')})",
            'total_revenue': split_data['gross_revenue'],
            'instructor_total': split_data['instructors_total'],
            'proform_share': split_data['proform_share'],
            'acr_share': split_data['acr_share'],
            'status': ProtocolPeriodSettlement.Status.DRAFT,
            'notes': notes,
        }
    )

    if not created and settlement.status == ProtocolPeriodSettlement.Status.DRAFT:
        settlement.total_revenue = split_data['gross_revenue']
        settlement.instructor_total = split_data['instructors_total']
        settlement.proform_share = split_data['proform_share']
        settlement.acr_share = split_data['acr_share']
        if notes:
            settlement.notes = notes
        settlement.save()

    return settlement
