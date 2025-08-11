"""
Comando para actualizar tasas de cambio
"""
from django.core.management.base import BaseCommand
from currency.services import CurrencyService


class Command(BaseCommand):
    help = 'Actualizar tasas de cambio desde la API externa'

    def add_arguments(self, parser):
        parser.add_argument(
            '--currencies',
            nargs='+',
            type=str,
            help='Lista específica de monedas a actualizar (ej: USD EUR)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar actualización aunque ya existan tasas recientes'
        )

    def handle(self, *args, **options):
        currencies = options.get('currencies', [])
        force_update = options.get('force', False)
        
        service = CurrencyService()
        
        self.stdout.write("Actualizando tasas de cambio...")
        
        if currencies:
            self.stdout.write(f"Monedas específicas: {', '.join(currencies)}")
        
        if force_update:
            self.stdout.write("Forzando actualización de tasas existentes")
        
        try:
            result = service.refresh_all_rates()
            
            self.stdout.write(f"\nResultados:")
            self.stdout.write(f"✓ Tasas actualizadas: {result['updated']}")
            
            if result['errors']:
                self.stdout.write(f"✗ Errores: {len(result['errors'])}")
                for error in result['errors']:
                    self.stderr.write(f"  - {error}")
            
            if result['updated'] > 0:
                self.stdout.write(self.style.SUCCESS(
                    f"Se actualizaron {result['updated']} tasas de cambio"
                ))
            else:
                self.stdout.write(self.style.WARNING("No se actualizaron tasas"))
                
        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f"Error actualizando tasas de cambio: {str(e)}"
            ))