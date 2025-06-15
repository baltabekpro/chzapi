import os
import sys
from PyPDF2 import PdfReader

def convert_pdf_to_text(pdf_path, output_path=None):
    """
    Конвертирует PDF в текстовый файл
    
    Args:
        pdf_path (str): Путь к PDF файлу
        output_path (str, optional): Путь для сохранения текстового файла. 
                                  По умолчанию имя PDF файла с расширением .txt
    
    Returns:
        str: Путь к созданному текстовому файлу
    """
    if not os.path.exists(pdf_path):
        print(f"Ошибка: Файл {pdf_path} не найден")
        return None
    
    if output_path is None:
        base_name = os.path.basename(pdf_path)
        name_without_ext = os.path.splitext(base_name)[0]
        output_path = os.path.join(os.path.dirname(pdf_path), f"{name_without_ext}.txt")
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf = PdfReader(file)
            text = ""
            
            for page_num in range(len(pdf.pages)):
                page = pdf.pages[page_num]
                text += page.extract_text()
                text += f"\n\n--- Страница {page_num + 1} ---\n\n"
            
            with open(output_path, 'w', encoding='utf-8') as output_file:
                output_file.write(text)
            
            print(f"Файл успешно конвертирован и сохранен как {output_path}")
            return output_path
    
    except Exception as e:
        print(f"Ошибка при конвертации PDF: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python pdf_to_text.py путь_к_pdf [путь_для_вывода]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    convert_pdf_to_text(pdf_path, output_path)
