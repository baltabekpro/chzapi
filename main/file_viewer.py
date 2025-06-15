import csv
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import colorama
from colorama import Back, Fore, Style

# Initialize colorama
colorama.init(autoreset=True)


class FileViewer:
    """Advanced file viewer with specialized rendering for different file types"""

    def __init__(self):
        self.current_dir = os.getcwd()

    def list_files(
        self, directory: str = None, filter_ext: List[str] = None
    ) -> List[str]:
        """List files in directory with optional extension filtering"""
        if directory is None:
            directory = self.current_dir

        try:
            files = os.listdir(directory)

            # Filter by extension if needed
            if filter_ext:
                files = [
                    f
                    for f in files
                    if any(f.lower().endswith(ext) for ext in filter_ext)
                ]

            return files
        except Exception as e:
            print(f"{Fore.RED}Error listing directory {directory}: {e}")
            return []

    def show_directory_content(
        self, directory: str = None, page_size: int = 20
    ) -> Optional[str]:
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
                os.system("cls" if os.name == "nt" else "clear")

                print(f"{Fore.CYAN}=== Содержимое директории: {directory} ===")
                print(f"{Fore.CYAN}=== Страница {current_page}/{total_pages} ===\n")

                # Calculate indices for current page
                start_idx = (current_page - 1) * page_size
                end_idx = min(start_idx + page_size, total_items)

                # Display items with numbers and icons
                for i, item in enumerate(
                    all_files[start_idx:end_idx], start=start_idx + 1
                ):
                    item_path = os.path.join(directory, item)
                    if os.path.isdir(item_path):
                        print(f"{Fore.GREEN}{i:3d}. 📁 {item}/")
                    else:
                        # Color by extension
                        ext = os.path.splitext(item)[1].lower()
                        if ext in (".py", ".js", ".html", ".css", ".php"):
                            print(f"{Fore.BLUE}{i:3d}. 📄 {item}")
                        elif ext in (".json", ".xml", ".yaml", ".yml", ".toml"):
                            print(f"{Fore.MAGENTA}{i:3d}. 🔧 {item}")
                        elif ext in (".txt", ".md", ".log", ".ini", ".cfg"):
                            print(f"{Fore.WHITE}{i:3d}. 📝 {item}")
                        elif ext in (".zip", ".rar", ".tar", ".gz", ".7z"):
                            print(f"{Fore.RED}{i:3d}. 📦 {item}")
                        elif ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp"):
                            print(f"{Fore.YELLOW}{i:3d}. 🖼️ {item}")
                        else:
                            print(f"{Fore.RESET}{i:3d}. 📄 {item}")

                print(f"\n{Fore.CYAN}Опции: [номер] для выбора, [N]ext, [P]rev, [Q]uit")
                choice = input(f"{Fore.YELLOW}Выберите файл или действие: ").strip()

                # Handle navigation
                if choice.lower() == "q":
                    return None
                elif choice.lower() == "n" and current_page < total_pages:
                    current_page += 1
                elif choice.lower() == "p" and current_page > 1:
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
                        input(
                            f"{Fore.RED}Неверный номер файла. Нажмите Enter для продолжения..."
                        )
                else:
                    input(f"{Fore.RED}Неверный ввод. Нажмите Enter для продолжения...")

        except Exception as e:
            print(f"{Fore.RED}Ошибка при просмотре директории: {e}")
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
            print(
                f"{Fore.YELLOW}Последнее изменение: {datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d %H:%M:%S')}"
            )
            print(f"{Fore.YELLOW}Тип файла: {ext[1:] if ext else 'Без расширения'}")
            print(f"{Fore.CYAN}{'=' * 50}\n")

            # Handle different file types
            if ext in (".json"):
                self.view_json_file(filepath)
            elif ext in (".csv"):
                self.view_csv_file(filepath)
            elif ext in (".log"):
                self.view_log_file(filepath)
            elif ext in (".py", ".js", ".html", ".css", ".php"):
                self.view_code_file(filepath, ext[1:])
            elif ext in (".md"):
                self.view_markdown_file(filepath)
            elif ext in (".txt", ".ini", ".cfg"):
                self.view_text_file(filepath)
            elif file_size > 1000:  # Large files (>1MB)
                self.view_large_file(filepath)
            else:
                self.view_text_file(filepath)  # Default view

        except Exception as e:
            print(f"{Fore.RED}Ошибка при просмотре файла: {e}")

    def view_json_file(self, filepath: str) -> None:
        """Pretty print JSON file"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Convert to formatted string with indentation
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)

            # Add syntax highlighting
            lines = formatted_json.split("\n")
            for line in lines:
                # Highlight keys
                if ":" in line:
                    key_part = line.split(":", 1)[0]
                    value_part = line.split(":", 1)[1]
                    print(f"{Fore.GREEN}{key_part}:{Fore.WHITE}{value_part}")
                else:
                    # Brackets and structural elements
                    if line.strip() in ("{", "}", "[", "]"):
                        print(f"{Fore.YELLOW}{line}")
                    else:
                        print(line)

        except json.JSONDecodeError:
            print(f"{Fore.RED}Ошибка: Файл не является корректным JSON")
            with open(filepath, "r", encoding="utf-8") as f:
                print(f.read())
        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении JSON: {e}")

    def view_csv_file(self, filepath: str, max_rows: int = 100) -> None:
        """Display CSV file as a table"""
        try:
            rows = []
            encodings = ["utf-8", "cp1251", "latin-1"]

            # Try different encodings
            for encoding in encodings:
                try:
                    with open(filepath, "r", encoding=encoding) as f:
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
                    print(
                        f"\n{Fore.YELLOW}... показано {max_rows} из {len(rows)} строк"
                    )

        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении CSV: {e}")

    def view_log_file(self, filepath: str, max_lines: int = 500) -> None:
        """Display log file with colorized output by log level"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Show only the last N lines for large log files
            if len(lines) > max_lines:
                print(
                    f"{Fore.YELLOW}Файл содержит {len(lines)} строк. Показаны последние {max_lines}.\n"
                )
                lines = lines[-max_lines:]

            # Regex patterns for common log formats
            date_pattern = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
            level_patterns = {
                "DEBUG": re.compile(r"\b(DEBUG|TRACE)\b", re.IGNORECASE),
                "INFO": re.compile(r"\bINFO\b", re.IGNORECASE),
                "WARNING": re.compile(r"\b(WARN|WARNING)\b", re.IGNORECASE),
                "ERROR": re.compile(r"\bERROR\b", re.IGNORECASE),
                "CRITICAL": re.compile(r"\b(CRITICAL|FATAL)\b", re.IGNORECASE),
            }

            for line in lines:
                line = line.rstrip()

                # Highlight timestamps
                date_match = date_pattern.search(line)
                if date_match:
                    date_part = date_match.group(0)
                    line = line.replace(
                        date_part, f"{Fore.CYAN}{date_part}{Style.RESET_ALL}"
                    )

                # Color by log level
                if level_patterns["CRITICAL"].search(line):
                    line = f"{Fore.RED}{Style.BRIGHT}{line}"
                elif level_patterns["ERROR"].search(line):
                    line = f"{Fore.RED}{line}"
                elif level_patterns["WARNING"].search(line):
                    line = f"{Fore.YELLOW}{line}"
                elif level_patterns["INFO"].search(line):
                    line = f"{Fore.GREEN}{line}"
                elif level_patterns["DEBUG"].search(line):
                    line = f"{Fore.BLUE}{line}"

                print(line)

        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении лога: {e}")

    def view_code_file(self, filepath: str, language: str) -> None:
        """Display code file with basic syntax highlighting"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()

            # Basic syntax highlighting
            lines = code.split("\n")

            # Common patterns to highlight
            keywords = {
                "py": [
                    "def",
                    "class",
                    "import",
                    "from",
                    "if",
                    "else",
                    "elif",
                    "for",
                    "while",
                    "return",
                    "try",
                    "except",
                    "finally",
                    "with",
                    "as",
                    "in",
                    "not",
                    "is",
                    "and",
                    "or",
                    "True",
                    "False",
                    "None",
                ],
                "js": [
                    "function",
                    "var",
                    "let",
                    "const",
                    "if",
                    "else",
                    "for",
                    "while",
                    "return",
                    "try",
                    "catch",
                    "finally",
                    "new",
                    "this",
                    "class",
                    "import",
                    "export",
                    "true",
                    "false",
                    "null",
                    "undefined",
                ],
                "html": [
                    "html",
                    "head",
                    "body",
                    "div",
                    "span",
                    "p",
                    "a",
                    "img",
                    "table",
                    "tr",
                    "td",
                    "th",
                    "ul",
                    "li",
                    "form",
                    "input",
                    "button",
                ],
                "css": [
                    "color",
                    "background",
                    "margin",
                    "padding",
                    "border",
                    "font",
                    "width",
                    "height",
                    "display",
                    "position",
                ],
            }

            lang_keywords = keywords.get(language, [])

            # Simple regex patterns for each language
            patterns = {
                "comment": re.compile(r"(#.*$|\/\/.*$|\/\*[\s\S]*?\*\/)", re.MULTILINE),
                "string": re.compile(r'(["\'])(?:(?=(\\?))\2.)*?\1'),
                "number": re.compile(r"\b\d+\b"),
                "keyword": re.compile(
                    r"\b(" + "|".join(map(re.escape, lang_keywords)) + r")\b"
                ),
            }

            for i, line in enumerate(lines, 1):
                # Line numbers
                print(f"{Fore.WHITE}{Style.DIM}{i:4d} ", end="")

                # Apply highlighting
                # First check comments (highest priority)
                comment_match = patterns["comment"].search(line)
                if comment_match:
                    comment_start = comment_match.start()
                    print(line[:comment_start], end="")
                    print(f"{Fore.GREEN}{Style.DIM}{line[comment_start:]}")
                    continue

                # Process the rest
                processed_line = line

                # Highlight strings
                for match in patterns["string"].finditer(line):
                    start, end = match.span()
                    processed_line = (
                        processed_line[:start]
                        + f"{Fore.YELLOW}{line[start:end]}{Style.RESET_ALL}"
                        + processed_line[end:]
                    )

                # Highlight keywords
                for match in patterns["keyword"].finditer(line):
                    start, end = match.span()
                    processed_line = (
                        processed_line[:start]
                        + f"{Fore.BLUE}{Style.BRIGHT}{line[start:end]}{Style.RESET_ALL}"
                        + processed_line[end:]
                    )

                # Highlight numbers
                for match in patterns["number"].finditer(line):
                    start, end = match.span()
                    processed_line = (
                        processed_line[:start]
                        + f"{Fore.MAGENTA}{line[start:end]}{Style.RESET_ALL}"
                        + processed_line[end:]
                    )

                print(processed_line)

        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении файла кода: {e}")

    def view_text_file(self, filepath: str, max_lines: int = 1000) -> None:
        """Display plain text file with line numbers"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Show only the first N lines for large files
            if len(lines) > max_lines:
                print(
                    f"{Fore.YELLOW}Файл содержит {len(lines)} строк. Показаны первые {max_lines}.\n"
                )
                lines = lines[:max_lines]

            for i, line in enumerate(lines, 1):
                print(f"{Fore.CYAN}{i:4d}{Style.RESET_ALL} {line}", end="")

            if len(lines) == 0:
                print(f"{Fore.YELLOW}Файл пуст.")

        except UnicodeDecodeError:
            try:
                with open(filepath, "r", encoding="cp1251") as f:
                    lines = f.readlines()

                for i, line in enumerate(lines, 1):
                    print(f"{Fore.CYAN}{i:4d}{Style.RESET_ALL} {line}", end="")
            except:
                print(f"{Fore.RED}Не удалось прочитать файл. Возможно бинарный формат.")
        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении файла: {e}")

    def view_large_file(
        self, filepath: str, head_lines: int = 20, tail_lines: int = 20
    ) -> None:
        """Display beginning and end of large files"""
        try:
            # Count total lines (fast method)
            line_count = 0
            with open(filepath, "r", encoding="utf-8") as f:
                for _ in f:
                    line_count += 1

            print(
                f"{Fore.YELLOW}Файл содержит {line_count} строк. Показаны первые {head_lines} и последние {tail_lines} строк.\n"
            )

            # Read head
            with open(filepath, "r", encoding="utf-8") as f:
                head = [next(f) for _ in range(head_lines)]

            # Read tail efficiently
            with open(filepath, "r", encoding="utf-8") as f:
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
                print(f"{Fore.CYAN}{i:4d}{Style.RESET_ALL} {line}", end="")

            if line_count > head_lines + tail_lines:
                print(
                    f"\n{Fore.YELLOW}... пропущено {line_count - head_lines - tail_lines} строк ...\n"
                )

            # Print tail
            print(f"{Fore.CYAN}=== Конец файла ==={Style.RESET_ALL}")
            for i, line in enumerate(tail, line_count - len(tail) + 1):
                print(f"{Fore.CYAN}{i:4d}{Style.RESET_ALL} {line}", end="")

        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении файла: {e}")

    def view_markdown_file(self, filepath: str) -> None:
        """Display markdown file with basic formatting"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                markdown = f.readlines()

            for line in markdown:
                line = line.rstrip()

                # Headers
                if line.startswith("# "):
                    print(f"{Fore.CYAN}{Style.BRIGHT}{line[2:]}")
                elif line.startswith("## "):
                    print(f"{Fore.CYAN}{line[3:]}")
                elif line.startswith("### "):
                    print(f"{Fore.BLUE}{line[4:]}")
                elif line.startswith("#### "):
                    print(f"{Fore.BLUE}{Style.DIM}{line[5:]}")
                # Lists
                elif line.strip().startswith("- ") or line.strip().startswith("* "):
                    print(f"{Fore.GREEN} • {line[2:]}")
                elif re.match(r"^\d+\. ", line.strip()):
                    print(f"{Fore.GREEN}{line}")
                # Code block
                elif line.startswith("```"):
                    print(f"{Fore.YELLOW}{line}")
                # Quote
                elif line.startswith(">"):
                    print(f"{Fore.MAGENTA}{Style.DIM}{line}")
                # Horizontal rule
                elif line.strip() == "---" or line.strip() == "***":
                    print(f"{Fore.WHITE}{Style.DIM}{'-' * 50}")
                # Bold and italic
                else:
                    # Highlight ** bold **
                    bold_pattern = re.compile(r"\*\*(.*?)\*\*")
                    line = bold_pattern.sub(f"{Style.BRIGHT}\\1{Style.NORMAL}", line)

                    # Highlight * italic *
                    italic_pattern = re.compile(r"\*(.*?)\*")
                    line = italic_pattern.sub(f"{Style.DIM}\\1{Style.NORMAL}", line)

                    # Highlight `code`
                    code_pattern = re.compile(r"`(.*?)`")
                    line = code_pattern.sub(f"{Fore.YELLOW}\\1{Fore.WHITE}", line)

                    print(line)

        except Exception as e:
            print(f"{Fore.RED}Ошибка при чтении Markdown файла: {e}")


def view_file_with_menu():
    """Main function to start file viewing interface"""
    viewer = FileViewer()

    # Clear screen
    os.system("cls" if os.name == "nt" else "clear")

    print(f"{Fore.CYAN}=== Просмотр файлов ===")
    print(f"{Fore.YELLOW}Навигация: выберите директорию и файл для просмотра")

    selected_file = viewer.show_directory_content()

    if selected_file and os.path.isfile(selected_file):
        # Clear screen before viewing file
        os.system("cls" if os.name == "nt" else "clear")
        viewer.view_file(selected_file)

        input(f"\n{Fore.GREEN}Нажмите Enter для возврата в меню...")


if __name__ == "__main__":
    view_file_with_menu()
