"""
Comando para procesar débitos automáticos pendientes
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from transactions.services import TransactionService


class Command(BaseCommand):
    help = 'Procesar débitos automáticos pendientes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué débitos se procesarían sin ejecutarlos'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write("Modo DRY RUN - No se ejecutarán débitos reales")
        
        service = TransactionService()
        
        # Obtener débitos pendientes
        from transactions.models import AutoDebit
        today = timezone.now().date()
        
        pending_debits = AutoDebit.objects.filter(
            status='active',
            next_execution__lte=today
        ).select_related('user', 'account', 'category')
        
        if not pending_debits.exists():
            self.stdout.write(self.style.SUCCESS("No hay débitos automáticos pendientes"))
            return
        
        self.stdout.write(f"Se encontraron {pending_debits.count()} débitos pendientes:")
        
        for debit in pending_debits:
            self.stdout.write(
                f"- {debit.name} ({debit.user.email}): ${debit.amount} {debit.currency} "
                f"desde {debit.account.name}"
            )
        
        if dry_run:
            return
        
        # Procesar débitos
        self.stdout.write("\nProcesando débitos...")
        result = service.execute_pending_debits()
        
        # Mostrar resultados
        self.stdout.write(f"\nResultados:")
        self.stdout.write(f"✓ Ejecutados exitosamente: {result['executed']}")
        
        if result['failed'] > 0:
            self.stdout.write(f"✗ Fallidos: {result['failed']}")
            for error in result['errors']:
                self.stderr.write(f"  - {error['auto_debit']}: {error['error']}")
        
        if result['executed'] > 0:
            self.stdout.write(self.style.SUCCESS(
                f"Se procesaron {result['executed']} débitos automáticos exitosamente"
            ))
        
        if result['failed'] > 0:
            self.stdout.write(self.style.WARNING(
                f"Falló el procesamiento de {result['failed']} débitos"
            ))