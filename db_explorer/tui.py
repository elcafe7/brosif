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


def _clip(value: object, width: int) -> str:
    text = str(value if value is not None else "").replace("\n", " ")
    return text[: max(0, width)]


class ExplorerTUI:
    def __init__(self, adapter: ExplorerAdapter, title: str = "Database Explorer"):
        self.adapter = adapter
        self.title = title
        self.query = ""
        self.results: list[SearchResult] = []
        self.selected = 0
        self.detail: RecordDetail | None = None
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

    def _schedule_search(self) -> None:
        self.generation += 1
        self.deadline = time.monotonic() + DEBOUNCE_SECONDS
        self.detail = None
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

        screen.addnstr(0, 2, self.title, width - 3, curses.A_BOLD)
        screen.addnstr(2, 2, f"> {self.query}", width - 3)

        available = height - 6
        offset = max(
            0,
            min(
                self.selected - available // 2,
                max(0, len(self.results) - available),
            ),
        )
        for row_number, result in enumerate(self.results[offset : offset + available]):
            index = offset + row_number
            line = f"{result.label:<14} {result.title}"
            style = curses.A_REVERSE if index == self.selected else curses.A_NORMAL
            screen.addnstr(4 + row_number, 2, line, width - 3, style)

        if error_message:
            status = f"Error: {error_message}"
        elif self.deadline is not None:
            status = "waiting to search..."
        else:
            status = f"{len(self.results)} results | arrows navigate | Enter opens"
        screen.addnstr(height - 1, 2, status, width - 3, curses.A_DIM)
        screen.move(2, min(width - 2, len(self.query) + 4))
        screen.refresh()

    def _draw_detail(self, screen: curses.window, height: int, width: int) -> None:
        assert self.detail is not None
        screen.addnstr(
            0, 2, f"Record {self.detail.key}", width - 3, curses.A_BOLD
        )
        y = 2
        for name, value in self.detail.fields:
            if y >= height - 2:
                break
            screen.addnstr(y, 2, name, width - 3, curses.A_BOLD)
            y += 1
            for line in str(value if value is not None else "").splitlines() or [""]:
                if y >= height - 2:
                    break
                screen.addnstr(y, 4, _clip(line, width - 5), width - 5)
                y += 1
            y += 1
        screen.addnstr(height - 1, 2, "Esc/q returns to results", width - 3, curses.A_DIM)
        screen.refresh()
