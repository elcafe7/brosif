"""Reactive curses interface with debounced background database queries."""

from __future__ import annotations

import concurrent.futures
import curses
import curses.ascii
import queue
import time

from .adapter import ExplorerAdapter
from .models import RecordDetail, SearchResult

DEBOUNCE_SECONDS = 0.15

# Curses color pairs (initialized in _init_colors)
PAIR_HEADER = 1
PAIR_PROMPT = 2
PAIR_GROUP = 3
PAIR_SELECTED = 4
PAIR_DIM = 5
PAIR_FIELD = 6


def _wrap(value: object, width: int) -> list[str]:
    text = str(value if value is not None else "")
    if width <= 0:
        return [text]
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        while len(paragraph) > width:
            break_at = paragraph.rfind(" ", 0, width)
            if break_at <= 0:
                break_at = width
            lines.append(paragraph[:break_at])
            paragraph = paragraph[break_at:].lstrip()
        lines.append(paragraph)
    return lines or [""]


class ExplorerTUI:
    def __init__(self, adapter: ExplorerAdapter, title: str = "Database Explorer"):
        self.adapter = adapter
        self.title = title
        self.query = ""
        self.results: list[SearchResult] = []
        self.selected = 0
        self.detail: RecordDetail | None = None
        self.detail_offset = 0
        self.generation = 0
        self.deadline: float | None = None
        self.responses: queue.SimpleQueue[
            tuple[int, list[SearchResult] | Exception]
        ] = queue.SimpleQueue()
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="db-explorer"
        )

    def run(self) -> None:
        try:
            curses.wrapper(self._main)
        finally:
            self.executor.shutdown(wait=False, cancel_futures=True)

    def _init_colors(self) -> None:
        if not curses.has_colors():
            return
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(PAIR_HEADER, curses.COLOR_CYAN, -1)
        curses.init_pair(PAIR_PROMPT, curses.COLOR_GREEN, -1)
        curses.init_pair(PAIR_GROUP, curses.COLOR_CYAN, -1)
        curses.init_pair(PAIR_SELECTED, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(PAIR_DIM, curses.COLOR_WHITE, -1)
        curses.init_pair(PAIR_FIELD, curses.COLOR_CYAN, -1)

    def _schedule_search(self) -> None:
        self.generation += 1
        self.deadline = time.monotonic() + DEBOUNCE_SECONDS
        self.detail = None
        self.detail_offset = 0
        self.selected = 0
        if not self.query:
            self.results = []

    def _submit_search(self) -> None:
        generation = self.generation
        query_text = self.query
        self.deadline = None

        def execute() -> None:
            try:
                response: list[SearchResult] | Exception = self.adapter.search(query_text)
            except Exception as error:  # surfaced in the interface
                response = error
            self.responses.put((generation, response))

        self.executor.submit(execute)

    def _collect_responses(self) -> str | None:
        error_message = None
        while True:
            try:
                generation, response = self.responses.get_nowait()
            except queue.Empty:
                break
            if generation != self.generation:
                continue
            if isinstance(response, Exception):
                error_message = str(response)
                self.results = []
            else:
                self.results = response
                self.selected = min(self.selected, max(0, len(response) - 1))
        return error_message

    def _main(self, screen: curses.window) -> None:
        self._init_colors()
        try:
            curses.curs_set(1)
        except curses.error:
            pass
        screen.keypad(True)
        screen.timeout(40)
        error_message = None

        while True:
            if self.deadline is not None and time.monotonic() >= self.deadline:
                self._submit_search()
            error_message = self._collect_responses() or error_message
            self._draw(screen, error_message)

            key = screen.getch()
            if key == -1:
                continue
            error_message = None

            if self.detail is not None:
                if key in (27, ord("q"), curses.KEY_BACKSPACE, 127):
                    self.detail = None
                    self.detail_offset = 0
                elif key == curses.KEY_UP:
                    self.detail_offset = max(0, self.detail_offset - 1)
                elif key == curses.KEY_DOWN:
                    self.detail_offset += 1
                elif key == curses.KEY_PPAGE:
                    self.detail_offset = max(0, self.detail_offset - 10)
                elif key == curses.KEY_NPAGE:
                    self.detail_offset += 10
                elif key == curses.KEY_HOME:
                    self.detail_offset = 0
                continue

            if key == 27:
                if self.query:
                    self.query = ""
                    self._schedule_search()
                else:
                    return
            elif key in (10, 13):
                if self.results:
                    try:
                        self.detail = self.adapter.detail(
                            self.results[self.selected].key
                        )
                        self.detail_offset = 0
                    except Exception as error:
                        error_message = str(error)
            elif key in (curses.KEY_BACKSPACE, 127, curses.ascii.BS):
                if self.query:
                    self.query = self.query[:-1]
                    self._schedule_search()
            elif key == curses.KEY_UP:
                self.selected = max(0, self.selected - 1)
            elif key == curses.KEY_DOWN:
                self.selected = min(max(0, len(self.results) - 1), self.selected + 1)
            elif key == curses.KEY_HOME:
                self.selected = 0
            elif key == curses.KEY_END:
                self.selected = max(0, len(self.results) - 1)
            elif 32 <= key <= 126:
                self.query += chr(key)
                self._schedule_search()

    def _draw(self, screen: curses.window, error_message: str | None) -> None:
        height, width = screen.getmaxyx()
        screen.erase()
        if height < 8 or width < 40:
            screen.addnstr(0, 0, "Terminal must be at least 40x8", width - 1)
            screen.refresh()
            return

        if self.detail is not None:
            self._draw_detail(screen, height, width)
            return

        screen.addnstr(0, 2, self.title, width - 3,
                        curses.color_pair(PAIR_HEADER) | curses.A_BOLD)
        screen.addnstr(2, 2, f"> {self.query}", width - 3,
                        curses.color_pair(PAIR_PROMPT))

        available = height - 6
        display_rows: list[tuple[int | None, str]] = []
        previous_group = None
        for index, result in enumerate(self.results):
            if result.group and result.group != previous_group:
                display_rows.append((None, f"▾ {result.group}"))
                previous_group = result.group
            display_rows.append((index, f"  {result.title}  ·  {result.label}"))

        selected_row = next(
            (
                row_number
                for row_number, (result_index, _) in enumerate(display_rows)
                if result_index == self.selected
            ),
            0,
        )
        offset = max(
            0,
            min(
                selected_row - available // 2,
                max(0, len(display_rows) - available),
            ),
        )
        for row_number, (result_index, line) in enumerate(
            display_rows[offset : offset + available]
        ):
            if result_index is None:
                style = curses.color_pair(PAIR_GROUP) | curses.A_BOLD | curses.A_UNDERLINE
            elif result_index == self.selected:
                style = curses.color_pair(PAIR_SELECTED)
            else:
                style = curses.A_NORMAL
            screen.addnstr(4 + row_number, 2, line, width - 3, style)

        if error_message:
            status = f"Error: {error_message}"
        elif self.deadline is not None:
            status = "waiting to search..."
        else:
            status = f"{len(self.results)} results | arrows navigate | Enter opens"
        screen.addnstr(height - 1, 2, status, width - 3,
                        curses.color_pair(PAIR_DIM) | curses.A_DIM)
        screen.move(2, min(width - 2, len(self.query) + 4))
        screen.refresh()

    def _draw_detail(self, screen: curses.window, height: int, width: int) -> None:
        assert self.detail is not None
        screen.addnstr(
            0, 2, f"Record {self.detail.key}", width - 3,
            curses.color_pair(PAIR_HEADER) | curses.A_BOLD
        )
        content: list[tuple[str, int]] = []
        for name, value in self.detail.fields:
            content.append((name, curses.color_pair(PAIR_FIELD) | curses.A_BOLD))
            for line in _wrap(value, width - 5):
                content.append((f"  {line}", curses.A_NORMAL))
            content.append(("", curses.A_NORMAL))

        available = height - 3
        max_offset = max(0, len(content) - available)
        self.detail_offset = min(self.detail_offset, max_offset)
        for row_number, (line, style) in enumerate(
            content[self.detail_offset : self.detail_offset + available]
        ):
            screen.addnstr(2 + row_number, 2, line, width - 3, style)
        status = (
            f"lines {self.detail_offset + 1}-{min(len(content), self.detail_offset + available)}"
            f"/{len(content)} | arrows/PgUp/PgDn scroll | Esc/q returns"
        )
        screen.addnstr(height - 1, 2, status, width - 3,
                        curses.color_pair(PAIR_DIM) | curses.A_DIM)
        screen.refresh()
