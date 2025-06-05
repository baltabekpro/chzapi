import os
import json
import sys
import csv
import re
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import colorama
from colorama import Fore, Back, Style
from logger_config import get_logger, log_exception

# Initialize colorama for colored terminal output
colorama.init(autoreset=True)

# Set up logger
files_logger = get_logger("files")

class FileViewer:
    """Advanced file viewer with specialized rendering for different file types"""
    
    def __init__(self):
        self.current_dir = os.getcwd()
        
    def list_files(self, directory: str = None, filter_ext: List[str] = None) -> List[str]:
        """List files in directory with optional extension filtering"""
        if directory is None:
            directory = self.current_dir
            
        try:
            files = os.listdir(directory)
            
            # Filter by extension if needed
            if filter_ext:
                files = [f for f in files if any(f.lower().endswith(ext) for ext in filter_ext)]
                
            return files
        except Exception as e:
            print(f"{Fore.RED}Error listing directory {directory}: {e}")
            return []
            
    def show_directory_content(self, directory: str = None, page_size: int = 20) -> Optional[str]:
        """Show directory content with pagination and numbering"""
        if directory is None:
            directory = self.current_dir
            
        try:
            all_files = []
            files = []
            dirs = []
            
            # Separate files and directories
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    files.append(item)
                else:
                    dirs.append(item)
            
            # Sort alphabetically
            dirs.sort()
            files.sort()
            
            # Combine with directories first
            all_files = dirs + files
            
            if not all_files:
                print(f"{Fore.YELLOW}Директория пуста.")
                return None
                
            # Display with pagination
            total_items = len(all_files)
            total_pages = (total_items + page_size - 1) // page_size
            current_page = 1
            
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
                
                print(f"{Fore.CYAN}=== Содержимое директории: {directory} ===")
                print(f"{Fore.CYAN}=== Страница {current_page}/{total_pages} ===\n")
                
                # Calculate indices for current page
                start_idx = (current_page - 1) * page_size
                end_idx = min(start_idx + page_size, total_items)
                
                # Display items with numbers and icons
                for i, item in enumerate(all_files[start_idx:end_idx], start=start_idx + 1):
                    item_path = os.path.join(directory, item)
                    if os.path.isdir(item_path):
                        print(f"{Fore.GREEN}{i:3d}. 📁 {item}/")
                    else:
                        # Color by extension
                        ext = os.path.splitext(item)[1].lower()
                        if ext in ('.py', '.js', '.html', '.css', '.php'):
                            print(f"{Fore.BLUE}{i:3d}. 📄 {item}")
                        elif ext in ('.json', '.xml', '.yaml', '.yml', '.toml'):
                            print(f"{Fore.MAGENTA}{i:3d}. 🔧 {item}")
                        elif ext in ('.txt', '.md', '.log', '.ini', '.cfg'):
                            print(f"{Fore.WHITE}{i:3d}. 📝 {item}")
                        elif ext in ('.zip', '.rar', '.tar', '.gz', '.7z'):
                            print(f"{Fore.RED}{i:3d}. 📦 {item}")
                        elif ext in ('.jpg', '.jpeg', '.png', '.gif', '.bmp'):
                            print(f"{Fore.YELLOW}{i:3d}. 🖼️ {item}")
                        else:
                            print(f"{Fore.RESET}{i:3d}. 📄 {item}")
                
                print(f"\n{Fore.CYAN}Опции: [номер] для выбора, [N]ext, [P]rev, [B]ack, [Q]uit")
                choice = input(f"{Fore.YELLOW}Выберите файл или действие: ").strip()
                
                # Handle navigation
                if choice.lower() == 'q':
                    return None
                elif choice.lower() == 'b':
                    parent_dir = os.path.dirname(directory)
                    return self.show_directory_content(parent_dir)
                elif choice.lower() == 'n' and current_page < total_pages:
                    current_page += 1
                elif choice.lower() == 'p' and current_page > 1:
                    current_page -= 1
                elif choice.isdigit():
                    item_num = int(choice)
                    if 1 <= item_num <= total_items:
                        selected_file = all_files[item_num - 1]
                        selected_path = os.path.join(directory, selected_file)
                        
                        if os.path.isdir(selected_path):
                            self.current_dir = selected_path
                            return self.show_directory_content(selected_path)
                        else:
                            return selected_path
                    else:
                        input(f"{Fore.RED}Неверный номер файла. Нажмите Enter для продолжения...")
                else:
                    input(f"{Fore.RED}Неверный ввод. Нажмите Enter для продолжения...")
                
        except Exception as e:
            print(f"{Fore.RED}Ошибка при просмотре директории: {e}")
            files_logger.error(f"Error browsing directory: {str(e)}")
            input("Нажмите Enter для продолжения...")
            return None
            
    def view_file(self, filepath: str) -> None:
        """View file content with proper rendering based on file type"""
        if not os.path.exists(filepath):
            print(f"{Fore.RED}Файл не найден: {filepath}")
            return
            
        try:
            # Get file extension and size
            ext = os.path.splitext(filepath)[1].lower()
            filename = os.path.basename(filepath)
            file_size = os.path.getsize(filepath) / 1024  # KB
            
            # Print file info
            print(f"\n{Fore.CYAN}=== Просмотр файла: {filename} ===")
            print(f"{Fore.YELLOW}Размер: {file_size:.2f} KB")
            print(f"{Fore.YELLOW}Последнее изменение: {datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{Fore.YELLOW}Тип файла: {ext[1:] if ext else 'Без расширения'}")
            print(f"{Fore.CYAN}{'=' * 50}\n")
            
            # Handle different file types
            if ext in ('.json'):
                self.view_json_file(filepath)
            elif ext in ('.csv'):
                self.view_csv_file(filepath)
            elif ext in ('.log'):
                self.view_log_file(filepath)
            elif ext in ('.py', '.js', '.html', '.css', '.php'):
                self.view_code_file(filepath, ext[1:])
            elif ext in ('.md'):
                self.view_markdown_file(filepath)
            elif ext in ('.txt', '.ini', '.cfg'):
                self.view_text_file(filepath)
            elif file_size > 1000:  # Large files (>1MB)
                self.view_large_file(filepath)
            else:
                self.view_text_file(filepath)  # Default view
                
            # Log file view activity
            files_logger.info(f"Viewed file: {filepath}")
                
        except Exception as e:
            print(f"{Fore.RED}Ошибка при просмотре файла: {e}")
            files_logger.error(f"Error viewing file {filepath}: {str(e)}")
            
    def view_json_file(self, filepath: str) -> None:
        """Pretty print JSON file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to formatted string with indentation
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            
            # Add syntax highlighting
            lines = formatted_json.split('\n')
            for line in lines:
                # Highlight keys
                if ':' in line:
                    key_part = line.split(':', 1)[0]
                    value_part = line.split(':', 1)[1]
                    print(f"{Fore.GREEN}{key_part}:{Fore.WHITE}{value_part}")
                else:
                    # Brackets and structural elements
                    if line.strip() in ('{', '}', '[', ']'):
                        print(f"{Fore.YELLOW}{line}")
                    else:
                        print(line)
            
        except json.JSONDecodeError:
            print(f"{Fore.RED}Ошибка: Файл не является корректным JSON")
            with open(filepath, 'r', encoding='utf-8') as f:
                print(f.read())
        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении JSON: {e}")
            
    def view_csv_file(self, filepath: str, max_rows: int = 100) -> None:
        """Display CSV file as a table"""
        try:
            rows = []
            encodings = ['utf-8', 'cp1251', 'latin-1']
            
            # Try different encodings
            for encoding in encodings:
                try:
                    with open(filepath, 'r', encoding=encoding) as f:
                        csv_reader = csv.reader(f)
                        rows = list(csv_reader)
                    break
                except UnicodeDecodeError:
                    continue
                    
            if not rows:
                print(f"{Fore.RED}Не удалось прочитать CSV файл")
                return
                
            # Find the maximum width for each column
            col_widths = []
            for row in rows[:max_rows]:
                while len(col_widths) < len(row):
                    col_widths.append(0)
                for i, cell in enumerate(row):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
            
            # Print header
            if rows:
                header = rows[0]
                header_line = " | ".join(
                    f"{Fore.CYAN}{header[i]:{col_widths[i]}}" 
                    for i in range(min(len(header), len(col_widths)))
                )
                print(header_line)
                print("-" * (sum(col_widths) + 3 * len(col_widths)))
                
                # Print data rows
                for row in rows[1:max_rows]:
                    data_line = " | ".join(
                        f"{Fore.WHITE}{row[i]:{col_widths[i]}}" 
                        for i in range(min(len(row), len(col_widths)))
                    )
                    print(data_line)
                    
                if len(rows) > max_rows:
                    print(f"\n{Fore.YELLOW}... показано {max_rows} из {len(rows)} строк")
                
        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении CSV: {e}")
            
    def view_log_file(self, filepath: str, max_lines: int = 500) -> None:
        """Display log file with colorized output by log level"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Show only the last N lines for large log files
            if len(lines) > max_lines:
                print(f"{Fore.YELLOW}Файл содержит {len(lines)} строк. Показаны последние {max_lines}.\n")
                lines = lines[-max_lines:]
                
            # Regex patterns for common log formats
            date_pattern = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}')
            level_patterns = {
                'DEBUG': re.compile(r'\b(DEBUG|TRACE)\b', re.IGNORECASE),
                'INFO': re.compile(r'\bINFO\b', re.IGNORECASE),
                'WARNING': re.compile(r'\b(WARN|WARNING)\b', re.IGNORECASE),
                'ERROR': re.compile(r'\bERROR\b', re.IGNORECASE),
                'CRITICAL': re.compile(r'\b(CRITICAL|FATAL)\b', re.IGNORECASE),
            }
            
            for line in lines:
                line = line.rstrip()
                
                # Highlight timestamps
                date_match = date_pattern.search(line)
                if date_match:
                    date_part = date_match.group(0)
                    line = line.replace(date_part, f"{Fore.CYAN}{date_part}{Style.RESET_ALL}")
                
                # Color by log level
                if level_patterns['CRITICAL'].search(line):
                    line = f"{Fore.RED}{Style.BRIGHT}{line}"
                elif level_patterns['ERROR'].search(line):
                    line = f"{Fore.RED}{line}"
                elif level_patterns['WARNING'].search(line):
                    line = f"{Fore.YELLOW}{line}"
                elif level_patterns['INFO'].search(line):
                    line = f"{Fore.GREEN}{line}"
                elif level_patterns['DEBUG'].search(line):
                    line = f"{Fore.BLUE}{line}"
                    
                print(line)
                
        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении лога: {e}")
            
    def view_code_file(self, filepath: str, language: str) -> None:
        """Display code file with basic syntax highlighting"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                code = f.read()
                
            # Basic syntax highlighting
            lines = code.split('\n')
            
            # Common patterns to highlight
            keywords = {
                'py': ['def', 'class', 'import', 'from', 'if', 'else', 'elif', 'for', 'while', 
                      'return', 'try', 'except', 'finally', 'with', 'as', 'in', 'not', 'is', 
                      'and', 'or', 'True', 'False', 'None'],
                'js': ['function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 'return', 
                      'try', 'catch', 'finally', 'new', 'this', 'class', 'import', 'export', 
                      'true', 'false', 'null', 'undefined'],
                'html': ['html', 'head', 'body', 'div', 'span', 'p', 'a', 'img', 'table', 'tr', 
                        'td', 'th', 'ul', 'li', 'form', 'input', 'button'],
                'css': ['color', 'background', 'margin', 'padding', 'border', 'font', 'width', 
                       'height', 'display', 'position']
            }
            
            lang_keywords = keywords.get(language, [])
            
            # Simple regex patterns for each language
            patterns = {
                'comment': re.compile(r'(#.*$|\/\/.*$|\/\*[\s\S]*?\*\/)', re.MULTILINE),
                'string': re.compile(r'(["\'])(?:(?=(\\?))\2.)*?\1'),
                'number': re.compile(r'\b\d+\b'),
                'keyword': re.compile(r'\b(' + '|'.join(map(re.escape, lang_keywords)) + r')\b')
            }
            
            for i, line in enumerate(lines, 1):
                # Line numbers
                print(f"{Fore.WHITE}{Style.DIM}{i:4d} ", end='')
                
                # Apply highlighting
                # First check comments (highest priority)
                comment_match = patterns['comment'].search(line)
                if comment_match:
                    comment_start = comment_match.start()
                    print(line[:comment_start], end='')
                    print(f"{Fore.GREEN}{Style.DIM}{line[comment_start:]}")
                    continue
                    
                # Process the rest
                processed_line = line
                
                # Highlight strings
                for match in patterns['string'].finditer(line):
                    start, end = match.span()
                    processed_line = (
                        processed_line[:start] + 
                        f"{Fore.YELLOW}{line[start:end]}{Style.RESET_ALL}" + 
                        processed_line[end:]
                    )
                
                # Highlight keywords
                for match in patterns['keyword'].finditer(line):
                    start, end = match.span()
                    processed_line = (
                        processed_line[:start] + 
                        f"{Fore.BLUE}{Style.BRIGHT}{line[start:end]}{Style.RESET_ALL}" + 
                        processed_line[end:]
                    )
                
                # Highlight numbers
                for match in patterns['number'].finditer(line):
                    start, end = match.span()
                    processed_line = (
                        processed_line[:start] + 
                        f"{Fore.MAGENTA}{line[start:end]}{Style.RESET_ALL}" + 
                        processed_line[end:]
                    )
                    
                print(processed_line)
                
        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении файла кода: {e}")
            
    def view_text_file(self, filepath: str, max_lines: int = 1000) -> None:
        """Display plain text file with line numbers"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Show only the first N lines for large files
            if len(lines) > max_lines:
                print(f"{Fore.YELLOW}Файл содержит {len(lines)} строк. Показаны первые {max_lines}.\n")
                lines = lines[:max_lines]
                
            for i, line in enumerate(lines, 1):
                print(f"{Fore.CYAN}{i:4d}{Style.RESET_ALL} {line}", end='')
                
            if len(lines) == 0:
                print(f"{Fore.YELLOW}Файл пуст.")
                
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='cp1251') as f:
                    lines = f.readlines()
                    
                for i, line in enumerate(lines, 1):
                    print(f"{Fore.CYAN}{i:4d}{Style.RESET_ALL} {line}", end='')
            except:
                print(f"{Fore.RED}Не удалось прочитать файл. Возможно бинарный формат.")
        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении файла: {e}")
            
    def view_large_file(self, filepath: str, head_lines: int = 20, tail_lines: int = 20) -> None:
        """Display beginning and end of large files"""
        try:
            # Count total lines (fast method)
            line_count = 0
            with open(filepath, 'r', encoding='utf-8') as f:
                for _ in f:
                    line_count += 1
                    
            print(f"{Fore.YELLOW}Файл содержит {line_count} строк. Показаны первые {head_lines} и последние {tail_lines} строк.\n")
            
            # Read head
            with open(filepath, 'r', encoding='utf-8') as f:
                head = [next(f) for _ in range(head_lines)]
                
            # Read tail efficiently
            with open(filepath, 'r', encoding='utf-8') as f:
                if line_count > head_lines + tail_lines:
                    # Skip to appropriate position
                    for _ in range(line_count - tail_lines):
                        next(f, None)
                else:
                    # For smaller files, skip only what's needed
                    for _ in range(head_lines):
                        next(f, None)
                        
                tail = f.readlines()
                
            # Print head
            print(f"{Fore.CYAN}=== Начало файла ==={Style.RESET_ALL}")
            for i, line in enumerate(head, 1):
                print(f"{Fore.CYAN}{i:4d}{Style.RESET_ALL} {line}", end='')
                
            if line_count > head_lines + tail_lines:
                print(f"\n{Fore.YELLOW}... пропущено {line_count - head_lines - tail_lines} строк ...\n")
                
            # Print tail
            print(f"{Fore.CYAN}=== Конец файла ==={Style.RESET_ALL}")
            for i, line in enumerate(tail, line_count - len(tail) + 1):
                print(f"{Fore.CYAN}{i:4d}{Style.RESET_ALL} {line}", end='')
                
        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении файла: {e}")
            
    def view_markdown_file(self, filepath: str) -> None:
        """Display markdown file with basic formatting"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                markdown = f.readlines()
                
            for line in markdown:
                line = line.rstrip()
                
                # Headers
                if line.startswith('# '):
                    print(f"{Fore.CYAN}{Style.BRIGHT}{line[2:]}")
                elif line.startswith('## '):
                    print(f"{Fore.CYAN}{line[3:]}")
                elif line.startswith('### '):
                    print(f"{Fore.BLUE}{line[4:]}")
                elif line.startswith('#### '):
                    print(f"{Fore.BLUE}{Style.DIM}{line[5:]}")
                # Lists
                elif line.strip().startswith('- ') or line.strip().startswith('* '):
                    print(f"{Fore.GREEN} • {line[2:]}")
                elif re.match(r'^\d+\. ', line.strip()):
                    print(f"{Fore.GREEN}{line}")
                # Code block
                elif line.startswith('```'):
                    print(f"{Fore.YELLOW}{line}")
                # Quote
                elif line.startswith('>'):
                    print(f"{Fore.MAGENTA}{Style.DIM}{line}")
                # Horizontal rule
                elif line.strip() == '---' or line.strip() == '***':
                    print(f"{Fore.WHITE}{Style.DIM}{'-' * 50}")
                # Bold and italic
                else:
                    # Highlight ** bold **
                    bold_pattern = re.compile(r'\*\*(.*?)\*\*')
                    line = bold_pattern.sub(f"{Style.BRIGHT}\\1{Style.NORMAL}", line)
                    
                    # Highlight * italic *
                    italic_pattern = re.compile(r'\*(.*?)\*')
                    line = italic_pattern.sub(f"{Style.DIM}\\1{Style.NORMAL}", line)
                    
                    # Highlight `code`
                    code_pattern = re.compile(r'`(.*?)`')
                    line = code_pattern.sub(f"{Fore.YELLOW}\\1{Fore.WHITE}", line)
                    
                    print(line)
                    
        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении Markdown файла: {e}")


# File utility functions
def list_files_in_directory(directory=None, detailed=False):
    """Lists files in a directory with optional detailed information"""
    if directory is None:
        directory = os.getcwd()
    
    if not os.path.exists(directory):
        print(f"{Fore.RED}Директория не найдена.")
        files_logger.warning(f"Attempted to list non-existent directory: {directory}")
        return []
    
    files_logger.info(f"Listing files in directory: {directory}")
    
    try:
        files = os.listdir(directory)
        print(f"\n{Fore.CYAN}Содержимое директории {directory}:")
        print(f"{Fore.CYAN}{'=' * 80}")
        
        if detailed:
            # Print header
            print(f"{Fore.YELLOW}{'№':4} {'Имя файла':<40} {'Тип':<8} {'Размер':>10} {'Дата изменения':<20}")
            print(f"{Fore.YELLOW}{'-' * 80}")
            
            for i, fname in enumerate(sorted(files), 1):
                path = os.path.join(directory, fname)
                file_type = 'Папка' if os.path.isdir(path) else 'Файл'
                
                # Format size
                if os.path.isfile(path):
                    size = os.path.getsize(path)
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024**2:
                        size_str = f"{size/1024:.1f} KB"
                    elif size < 1024**3:
                        size_str = f"{size/1024**2:.1f} MB"
                    else:
                        size_str = f"{size/1024**3:.1f} GB"
                else:
                    size_str = "-"
                    
                # Format modification date
                mod_time = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
                
                # Use colors based on type
                if os.path.isdir(path):
                    print(f"{Fore.GREEN}{i:4d} {fname:<40} {file_type:<8} {size_str:>10} {mod_time:<20}")
                else:
                    print(f"{Fore.RESET}{i:4d} {fname:<40} {file_type:<8} {size_str:>10} {mod_time:<20}")
        else:
            # Simple listing
            for i, fname in enumerate(sorted(files), 1):
                path = os.path.join(directory, fname)
                if os.path.isdir(path):
                    print(f"{Fore.GREEN}{i:3d}. {fname}/ (папка)")
                else:
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in ('.py', '.js', '.html', '.css', '.php'):
                        print(f"{Fore.BLUE}{i:3d}. {fname}")
                    elif ext in ('.json', '.xml'):
                        print(f"{Fore.MAGENTA}{i:3d}. {fname}")
                    elif ext in ('.txt', '.md', '.log'):
                        print(f"{Fore.YELLOW}{i:3d}. {fname}")
                    else:
                        print(f"{Fore.RESET}{i:3d}. {fname}")
                    
        files_logger.info(f"Listed {len(files)} files/directories")
        return files
    except Exception as e:
        log_exception(files_logger, e, f"Error listing directory {directory}")
        return []

def delete_file(file_path=None):
    """Delete a file or directory with confirmation"""
    if file_path is None:
        file_path = input(f"{Fore.YELLOW}Введите полный путь к файлу для удаления: ").strip()
        
    if not os.path.exists(file_path):
        print(f"{Fore.RED}Указанный файл/папка не существует.")
        files_logger.warning(f"Attempted to delete non-existent file/directory: {file_path}")
        return False
        
    try:
        # Get file information
        is_dir = os.path.isdir(file_path)
        file_type = "папку" if is_dir else "файл"
        file_name = os.path.basename(file_path)
        
        # Ask for confirmation
        print(f"{Fore.YELLOW}Вы уверены, что хотите удалить {file_type} '{file_name}'?")
        confirmation = input(f"{Fore.RED}Это действие нельзя отменить (y/n): ").lower()
        
        if confirmation != 'y':
            print(f"{Fore.CYAN}Удаление отменено.")
            return False
            
        if is_dir:
            shutil.rmtree(file_path)
            print(f"{Fore.GREEN}Папка {file_name} успешно удалена.")
            files_logger.info(f"Deleted directory: {file_path}")
        else:
            os.remove(file_path)
            print(f"{Fore.GREEN}Файл {file_name} успешно удалён.")
            files_logger.info(f"Deleted file: {file_path}")
            
        return True
    except Exception as e:
        log_exception(files_logger, e, f"Error deleting file/directory: {file_path}")
        return False

def add_file(src=None, dest_dir=None):
    """Copy a file to another location"""
    if src is None:
        src = input(f"{Fore.YELLOW}Введите путь к исходному файлу: ").strip()
        
    if not os.path.isfile(src):
        print(f"{Fore.RED}Исходный файл не найден.")
        files_logger.warning(f"Attempted to add non-existent file: {src}")
        return False
        
    if dest_dir is None:
        dest_dir = input(f"{Fore.YELLOW}Введите путь к директории для копирования (или Enter для текущей): ").strip()
        if not dest_dir:
            dest_dir = os.getcwd()
            
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, os.path.basename(src))
    
    try:
        shutil.copy2(src, dest)
        print(f"{Fore.GREEN}Файл скопирован в {dest}")
        files_logger.info(f"Copied file from {src} to {dest}")
        return True
    except Exception as e:
        log_exception(files_logger, e, f"Error copying file from {src} to {dest}")
        return False

def check_last_run_info():
    """Check information about last and next run"""
    last_run_file = "last_run.json"
    if not os.path.exists(last_run_file):
        print(f"{Fore.YELLOW}Файл last_run.json не найден. Следующий запуск неизвестен.")
        files_logger.warning("File last_run.json not found")
        return None
        
    try:
        with open(last_run_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_run = datetime.fromisoformat(data.get('last_run'))
            certs_processed = data.get('certificates_processed', 0)
            manual_run = data.get('manual_run', False)
            
            # Next run at midnight of next day
            next_run = (last_run.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
            
            # Calculate time until next run
            now = datetime.now()
            time_until = next_run - now if next_run > now else timedelta(0)
            
            run_info = {
                'last_run': last_run,
                'next_run': next_run,
                'certificates_processed': certs_processed,
                'manual_run': manual_run,
                'time_until': time_until
            }
            
            # Print information
            print(f"\n{Fore.CYAN}=== Информация о запусках ===")
            print(f"{Fore.YELLOW}Последний запуск: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{Fore.YELLOW}Следующий запуск: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{Fore.YELLOW}Обработано сертификатов: {certs_processed}")
            print(f"{Fore.YELLOW}{'Ручной' if manual_run else 'Автоматический'} запуск")
            
            if time_until.total_seconds() > 0:
                hours, remainder = divmod(time_until.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                print(f"{Fore.GREEN}Времени до следующего запуска: {time_until.days} дней, {hours} часов, {minutes} минут")
            else:
                print(f"{Fore.RED}Время следующего запуска уже наступило")
                
            files_logger.info(f"Checked run information: next run at {next_run}")
            return run_info
            
    except Exception as e:
        log_exception(files_logger, e, f"Error reading file {last_run_file}")
        return None

def get_reports_list(base_dir='output'):
    """Get list of available reports by certificate"""
    if not os.path.exists(base_dir):
        print(f"{Fore.RED}Папка с отчетами не найдена.")
        files_logger.warning(f"Reports directory not found: {base_dir}")
        return {}
        
    reports = {}
    certificates = os.listdir(base_dir)
    
    for cert in certificates:
        cert_path = os.path.join(base_dir, cert)
        if os.path.isdir(cert_path):
            json_reports = [f for f in os.listdir(cert_path) if f.startswith('violations_') and f.endswith('.json')]
            if json_reports:
                reports[cert] = [
                    {
                        'filename': report,
                        'date': report.split('_')[1].split('.')[0],
                        'path': os.path.join(cert_path, report)
                    }
                    for report in json_reports
                ]
    
    return reports

def view_file_with_menu(filepath=None):
    """Main function to start file viewing interface"""
    viewer = FileViewer()
    
    # Clear screen
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print(f"{Fore.CYAN}=== Просмотр файлов ===")
    print(f"{Fore.YELLOW}Навигация: выберите директорию и файл для просмотра")
    
    if filepath:
        # If filepath is provided, view it directly
        if os.path.isfile(filepath):
            viewer.view_file(filepath)
            input(f"\n{Fore.GREEN}Нажмите Enter для возврата в меню...")
        elif os.path.isdir(filepath):
            # Start browsing from the provided directory
            selected_file = viewer.show_directory_content(filepath)
            if selected_file and os.path.isfile(selected_file):
                os.system('cls' if os.name == 'nt' else 'clear')
                viewer.view_file(selected_file)
                input(f"\n{Fore.GREEN}Нажмите Enter для возврата в меню...")
    else:
        # Otherwise start browsing from current directory
        selected_file = viewer.show_directory_content()
        
        if selected_file and os.path.isfile(selected_file):
            # Clear screen before viewing file
            os.system('cls' if os.name == 'nt' else 'clear')
            viewer.view_file(selected_file)
            
            input(f"\n{Fore.GREEN}Нажмите Enter для возврата в меню...")

if __name__ == "__main__":
    view_file_with_menu()