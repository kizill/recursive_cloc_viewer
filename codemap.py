#!/usr/bin/env python3
import curses
import os
import pathlib
import json
import subprocess
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class FileStats:
    lines: int = 0
    code_lines: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    
    @staticmethod
    def size_str(size: int):
        if size < 1000:
            return f"{size}"
        elif size < 1000 * 1000:
            return f"{size / 1000:.2f} KL"
        else:
            return f"{size / (1000 * 1000):.2f} ML"

    def add(self, other: 'FileStats'):
        self.lines=self.lines + other.lines
        self.code_lines=self.code_lines + other.code_lines
        self.blank_lines=self.blank_lines + other.blank_lines
        self.comment_lines=self.comment_lines + other.comment_lines

class CodeMap:
    def __init__(self):
        self.stats_cache: Dict[str, FileStats] = {}
        self.current_path = pathlib.Path.cwd()
        self.scroll_position = 0
        self.selected_index = 0
        self.entries: List[Tuple[str, FileStats]] = []

        # Verify scc is available
        try:
            subprocess.run(['scc', '--version'], capture_output=True)
        except FileNotFoundError:
            print("Error: 'scc' tool not found. Please install it from: https://github.com/boyter/scc")
            sys.exit(1)

    def count_file_lines(self, file_path: pathlib.Path) -> FileStats:
        if str(file_path) in self.stats_cache:
            return self.stats_cache[str(file_path)]
        result = FileStats()
        # Run scc with JSON output for the specific file
        call_result = subprocess.run(
            ['scc', '-f', 'json', str(file_path)],
            capture_output=True,
            text=True
        )
        if call_result.returncode == 0 and call_result.stdout.strip():
            data = json.loads(call_result.stdout)
            
            for lang_stat in data or []:
                stats = FileStats(
                    lines=lang_stat['Lines'],
                    code_lines=lang_stat['Code'],
                    blank_lines=lang_stat['Blank'],
                    comment_lines=lang_stat['Comment'],
                )
                result.add(stats)
            self.stats_cache[str(file_path)] = result
        return result

    def scan_directory(self, path: pathlib.Path) -> None:
        self.entries = []
        
        # Add parent directory entry if not in root
        if path != path.parent:
            self.entries.append(("..", None))

    
        # Run scc on the entire directory
        overall_stats = self.count_file_lines(path)
        self.entries.append((".", overall_stats))
            
            # Collect directories and files
        
        for entry in os.scandir(path):
            entry_path = pathlib.Path(entry.path)
            self.entries.append((entry_path.name, self.count_file_lines(entry_path) ))
        

    def run(self, stdscr: curses.window) -> None:
        try:
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)

            self.scan_directory(self.current_path)

            while True:
                stdscr.clear()
                height, width = stdscr.getmaxyx()

                # Draw header
                header = f" CodeMap - {self.current_path} "
                stdscr.addstr(0, 0, header.center(width), curses.A_REVERSE)
 
                # Draw column headers
                stdscr.addstr(1, 0, "Name".ljust(40))
                stdscr.addstr(1, 40, "Lines".rjust(8))
                stdscr.addstr(1, 48, "Code".rjust(8))
                stdscr.addstr(1, 56, "Blank".rjust(8))
                stdscr.addstr(1, 64, "Comment".rjust(8))

                # Draw entries
                visible_entries = self.entries[self.scroll_position:self.scroll_position + height - 3]
                for i, (name, stats) in enumerate(visible_entries):
                    y = i + 2
                    is_selected = i + self.scroll_position == self.selected_index
                    style = curses.A_REVERSE if is_selected else curses.A_NORMAL

                    if stats is None:  # Directory
                        stdscr.addstr(y, 0, name.ljust(40), style | curses.color_pair(2))
                    else:  # File
                        stdscr.addstr(y, 0, name.ljust(40), style | curses.color_pair(1))
                        stdscr.addstr(y, 40, FileStats.size_str(stats.lines).rjust(8), style)
                        stdscr.addstr(y, 48, FileStats.size_str(stats.code_lines).rjust(8), style)
                        stdscr.addstr(y, 56, FileStats.size_str(stats.blank_lines).rjust(8), style)
                        stdscr.addstr(y, 64, FileStats.size_str(stats.comment_lines).rjust(8), style)

                stdscr.refresh()

                # Handle input
                key = stdscr.getch()
                if key == ord('q'):
                    break
                elif key == ord('c') and (key & 0x1f):  # Check for Ctrl+C
                    break
                elif key == curses.KEY_UP and self.selected_index > 0:
                    self.selected_index -= 1
                    if self.selected_index < self.scroll_position:
                        self.scroll_position = self.selected_index
                elif key == curses.KEY_DOWN and self.selected_index < len(self.entries) - 1:
                    self.selected_index += 1
                    if self.selected_index >= self.scroll_position + height - 3:
                        self.scroll_position = self.selected_index - (height - 4)
                elif key in (curses.KEY_ENTER, 10, 13):
                    if self.selected_index < len(self.entries):
                        name, _ = self.entries[self.selected_index]
                        if name == "..":
                            self.current_path = self.current_path.parent
                        else:
                            new_path = self.current_path / name
                            if new_path.is_dir():
                                self.current_path = new_path
                        
                        self.scan_directory(self.current_path)
                        self.selected_index = 0
                        self.scroll_position = 0
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            pass
        finally:
            # Ensure terminal is restored properly
            curses.endwin()

def main():
    try:
        code_map = CodeMap()
        curses.wrapper(code_map.run)
    except KeyboardInterrupt:
        # Handle Ctrl+C at the top level
        print("\nExiting...")

if __name__ == "__main__":
    main() 
    #code_map = CodeMap()
    #code_map.scan_directory(pathlib.Path.cwd())