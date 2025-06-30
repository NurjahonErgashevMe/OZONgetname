import os
import logging
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from src.config import RESULTS_DIR

class ExcelExporter:
    def __init__(self, category_name, timestamp):
        self.logger = logging.getLogger('excel_exporter')
        self.category_name = category_name
        self.timestamp = timestamp
        self.workbook = None
        self.worksheet = None
        
        # Формируем имя файла
        self.excel_filename = os.path.join(
            RESULTS_DIR, 
            f"{self.category_name}_{self.timestamp}.xlsx"
        )
        self.logger.info(f"Файл результатов: {self.excel_filename}")

    def init_workbook(self):
        """Инициализация рабочей книги"""
        self.workbook = openpyxl.Workbook()
        self.worksheet = self.workbook.active
        self.worksheet.title = "Результаты парсинга Ozon"

    def save_results(self, results):
        """Сохранение результатов в Excel"""
        try:
            self.init_workbook()
            ws = self.worksheet
            
            # Заголовки с новыми полями
            headers = ['Название товара', 'Название продавца', 'Название компании', 'ИНН','Ссылка на товар']
            
            # Стили для заголовков
            header_font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
            header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
            header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            
            # Стили для данных
            data_font = Font(name='Arial', size=11)
            data_alignment = Alignment(horizontal='left', vertical='center', wrap_text=True)
            
            # Границы
            thin_border = Border(
                left=Side(style='thin'),
                right=Side(style='thin'),
                top=Side(style='thin'),
                bottom=Side(style='thin')
            )
            
            # Цвета для разных статусов
            status_colors = {
                'success': PatternFill(start_color='C6EFCE', end_color='C6EFCE', fill_type='solid'),
                'out_of_stock': PatternFill(start_color='FFEB9C', end_color='FFEB9C', fill_type='solid'),
                'error': PatternFill(start_color='FFC7CE', end_color='FFC7CE', fill_type='solid'),
                'not_found': PatternFill(start_color='E6E6E6', end_color='E6E6E6', fill_type='solid'),
                'seller_not_found': PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')
            }
            
            # Заголовки
            for col_num, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_num, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border
            
            # Данные
            for row_num, (url, product, seller, company_name, inn, status) in enumerate(results, 2):
                clean_product = self._clean_text_value(product)
                clean_seller = self._clean_text_value(seller)
                clean_company_name = self._clean_text_value(company_name)
                clean_inn = self._clean_text_value(inn)
                
                row_data = [ clean_product, clean_seller, clean_company_name, clean_inn, url]
                
                # Определяем цвет строки
                if status == "success" and "не найден" in clean_seller.lower():
                    row_fill = status_colors['seller_not_found']
                else:
                    row_fill = status_colors.get(status, None)
                
                for col_num, value in enumerate(row_data, 1):
                    cell = ws.cell(row=row_num, column=col_num, value=value)
                    cell.font = data_font
                    cell.alignment = data_alignment
                    cell.border = thin_border
                    
                    if row_fill:
                        cell.fill = row_fill
            
            # Настройки столбцов (ширина)
            column_widths = [60, 40, 30, 35, 75]  # Ссылка, Товар, Продавец, Компания, ИНН
            for col_num, width in enumerate(column_widths, 1):
                col_letter = get_column_letter(col_num)
                ws.column_dimensions[col_letter].width = width
            
            # Высота строк
            for row in range(1, len(results) + 2):
                ws.row_dimensions[row].height = 25
            
            # Автофильтр и закрепление
            if results:
                ws.auto_filter.ref = f"A1:E{len(results) + 1}"
            ws.freeze_panes = "A2"
            
            # Сохранение
            self.workbook.save(self.excel_filename)
            
            self.logger.info(f"Результаты сохранены в {self.excel_filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении Excel: {str(e)}")
            return False

    def _clean_text_value(self, value):
        """Очистка текстового значения"""
        if not value:
            return ""
        return str(value).replace('\n', ' ').replace('\r', ' ').strip()

    def get_filename(self):
        """Получение имени файла"""
        return self.excel_filename