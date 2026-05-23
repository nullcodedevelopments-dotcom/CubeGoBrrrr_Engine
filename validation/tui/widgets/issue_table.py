from __future__ import annotations
from typing import List, Optional, Set
from rich.text import Text
from textual.message import Message
from textual.widgets import DataTable
from ...core.models import Severity, ValidationIssue, ScanReport
from ..theme import THEME, severity_color

class IssueSelected(Message):
    def __init__(self, issue: ValidationIssue) -> None:
        super().__init__()
        self.issue = issue

class IssueTable(DataTable):
    DEFAULT_CSS = "IssueTable { height: 1fr; }"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._all_issues:   List[ValidationIssue] = []
        self._sev_filter:   Set[Severity]          = {Severity.ERROR, Severity.WARNING, Severity.INFO}
        self._text_filter:  str                    = ""

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.add_columns("Sev", "File", "Line", "Rule", "Message")

    def load_report(self, report: ScanReport) -> None:
        issues: List[ValidationIssue] = []
        for fr in report.file_reports:
            issues.extend(fr.all_issues)
        self.load_issues(issues)

    def load_file_report_issues(self, issues: List[ValidationIssue]) -> None:
        self.load_issues(issues)

    def load_issues(self, issues: List[ValidationIssue]) -> None:
        self._all_issues = issues
        self._apply_filters()

    def append_issue(self, issue: ValidationIssue) -> None:
        self._all_issues.append(issue)
        if self._matches(issue):
            self._add_row(issue)

    def filter_severity(self, levels: Set[Severity]) -> None:
        self._sev_filter = levels
        self._apply_filters()

    def filter_text(self, query: str) -> None:
        self._text_filter = query.lower()
        self._apply_filters()

    def _matches(self, issue: ValidationIssue) -> bool:
        if issue.severity not in self._sev_filter:
            return False
        if self._text_filter and self._text_filter not in issue.message.lower():
            return False
        return True

    def _apply_filters(self) -> None:
        self.clear()
        for issue in self._all_issues:
            if self._matches(issue):
                self._add_row(issue)

    def _add_row(self, issue: ValidationIssue) -> None:
        sev_color = severity_color(issue.severity.value)
        sev_cell  = Text(issue.severity.value[:4], style=f"bold {sev_color}")
        file_cell = Text(issue.file_path.name, style=THEME["white"])
        line_cell = Text(str(issue.line), style=THEME["dim"])
        rule_cell = Text(issue.rule, style=THEME["magenta"])
        msg_cell  = Text(issue.message[:72])
        self.add_row(sev_cell, file_cell, line_cell, rule_cell, msg_cell, key=str(id(issue)))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key and event.row_key.value:
            row_id = event.row_key.value
            for issue in self._all_issues:
                if str(id(issue)) == row_id:
                    self.post_message(IssueSelected(issue))
                    break
