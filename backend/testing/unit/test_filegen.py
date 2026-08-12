"""
Unit tests for file_generator.py

The module under test drives a real Chromium browser (via Playwright) and
does real PDF manipulation (via pypdf) to produce a ZIP of report PDFs.
None of that is something a unit test should actually spin up, so these
tests replace Playwright's `sync_playwright`, and pypdf's `PdfReader`,
`PdfWriter`, and `PageObject`, with lightweight fakes that let us assert on
*control flow* (which files get written, in what order, with what names,
how merging/blank-page logic behaves) without needing a browser or real
PDF bytes.

Run with:  pytest test_file_generator.py -v
"""
import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest
import sys
from pathlib import Path
# Add the parent directory (backend) to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import filegen as fg
from processing import TOPIC_MAP


# ---------------------------------------------------------------------------
# Fakes for Playwright
# ---------------------------------------------------------------------------

class FakePage:
    """Stands in for a Playwright Page. Returns fake PDF bytes on .pdf()."""

    def __init__(self, pdf_bytes_sequence):
        # pdf_bytes_sequence: list of bytes to return, one per call to .pdf()
        self._pdf_bytes_sequence = list(pdf_bytes_sequence)
        self.set_content_calls = []
        self.pdf_calls = []
        self.closed = False

    def set_content(self, html, wait_until=None):
        self.set_content_calls.append(html)

    def pdf(self, **kwargs):
        self.pdf_calls.append(kwargs)
        if not self._pdf_bytes_sequence:
            raise AssertionError("FakePage.pdf() called more times than expected")
        return self._pdf_bytes_sequence.pop(0)

    def close(self):
        self.closed = True


class FakeBrowser:
    def __init__(self, page):
        self._page = page
        self.closed = False

    def new_page(self):
        return self._page

    def close(self):
        self.closed = True


class FakeChromium:
    def __init__(self, browser):
        self._browser = browser
        self.launch_kwargs = None

    def launch(self, **kwargs):
        self.launch_kwargs = kwargs
        return self._browser


class FakePlaywrightContext:
    def __init__(self, chromium):
        self.chromium = chromium

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def make_fake_sync_playwright(page):
    """Builds a drop-in replacement for `sync_playwright` returning `page`."""
    browser = FakeBrowser(page)
    chromium = FakeChromium(browser)
    context = FakePlaywrightContext(chromium)
    return MagicMock(return_value=context), browser, chromium


# ---------------------------------------------------------------------------
# Fakes for pypdf
# ---------------------------------------------------------------------------

class FakePdfPage:
    def __init__(self):
        self.mediabox = MagicMock(width=612.0, height=792.0)


class FakePdfReader:
    """Queue-driven fake: each instantiation pops the next page-count off
    a shared queue, so callers control exactly how many "pages" each
    fake PDF document reports."""

    page_count_queue = []

    def __init__(self, stream):
        self.stream = stream
        if not FakePdfReader.page_count_queue:
            raise AssertionError("FakePdfReader instantiated more times than expected")
        count = FakePdfReader.page_count_queue.pop(0)
        self.pages = [FakePdfPage() for _ in range(count)]


class FakePdfWriter:
    def __init__(self):
        self.added_pages = []
        self.written_buffers = []
        self.closed = False

    def add_page(self, page):
        self.added_pages.append(page)

    def write(self, buffer):
        buffer.write(b"%FAKE-MERGED-PDF%")
        self.written_buffers.append(buffer)

    def close(self):
        self.closed = True


class FakePageObject:
    @staticmethod
    def create_blank_page(width, height):
        blank = MagicMock()
        blank.width = width
        blank.height = height
        blank.is_blank = True
        return blank


# ---------------------------------------------------------------------------
# Shared test data helpers
# ---------------------------------------------------------------------------

def make_results(n=2):
    results = {}
    for i in range(1, n + 1):
        results[f"A0100000{i}"] = {
            "name": f"Student{i} T.",
            "score": "50.0%",
            "topics_to_review": ["2.1", "2.3"],
        }
    return results


def make_class_data():
    return {
        "average": 62.5,
        "missed_topics": [("2.1", 5), ("2.3", 3), ("2.5", 0)],
    }


@pytest.fixture
def patched_image(monkeypatch):
    """Avoid any real network call for the mascot image in file_generator_sync tests."""
    monkeypatch.setattr(fg, "get_image_base64", lambda url: "data:image/png;base64,FAKE")


@pytest.fixture
def patched_pypdf(monkeypatch):
    FakePdfReader.page_count_queue = []
    monkeypatch.setattr(fg, "PdfReader", FakePdfReader)
    monkeypatch.setattr(fg, "PdfWriter", FakePdfWriter)
    monkeypatch.setattr(fg, "PageObject", FakePageObject)
    yield
    FakePdfReader.page_count_queue = []


def install_fake_playwright(monkeypatch, page):
    fake_sync_playwright, browser, chromium = make_fake_sync_playwright(page)
    monkeypatch.setattr(fg, "sync_playwright", fake_sync_playwright)
    return browser, chromium


def zip_names(zip_buffer):
    zip_buffer.seek(0)
    with zipfile.ZipFile(zip_buffer) as zf:
        return zf.namelist()


# ---------------------------------------------------------------------------
# get_image_base64
# ---------------------------------------------------------------------------

class TestGetImageBase64:
    def test_fetches_and_encodes_remote_image(self, monkeypatch):
        fake_bytes = b"\x89PNG-fake-bytes"

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return fake_bytes

        monkeypatch.setattr(
            fg.urllib.request, "urlopen", lambda req: FakeResponse()
        )

        result = fg.get_image_base64("https://example.com/mascot.png")
        assert result.startswith("data:image/png;base64,")
        import base64
        encoded = result.split(",", 1)[1]
        assert base64.b64decode(encoded) == fake_bytes

    def test_reads_and_encodes_local_file(self, tmp_path):
        img_path = tmp_path / "mascot.png"
        img_path.write_bytes(b"local-image-bytes")

        result = fg.get_image_base64(str(img_path))
        assert result.startswith("data:image/png;base64,")

    def test_returns_empty_string_on_network_failure(self, monkeypatch):
        def raise_error(req):
            raise OSError("network unreachable")

        monkeypatch.setattr(fg.urllib.request, "urlopen", raise_error)
        result = fg.get_image_base64("https://example.com/mascot.png")
        assert result == ""

    def test_returns_empty_string_when_local_file_missing(self):
        result = fg.get_image_base64("/nonexistent/path/mascot.png")
        assert result == ""


# ---------------------------------------------------------------------------
# generate_html
# ---------------------------------------------------------------------------

class TestGenerateHtml:
    def test_includes_student_name_in_greeting(self):
        html = fg.generate_html(
            "A01234567", {"name": "Rafael R.", "topics_to_review": []}, "img-src"
        )
        assert "Dear Rafael R.," in html

    def test_falls_back_to_student_id_when_name_missing(self):
        html = fg.generate_html(
            "A01234567", {"name": "Name Missing", "topics_to_review": []}, "img-src"
        )
        assert "Dear Student (A01234567)," in html

    def test_renders_topic_titles_from_topic_map(self):
        html = fg.generate_html(
            "A01234567",
            {"name": "Rafael R.", "topics_to_review": ["2.1", "2.3"]},
            "img-src",
        )
        assert TOPIC_MAP["2.1"] in html
        assert TOPIC_MAP["2.3"] in html
        assert 'class="section-item"' in html

    def test_shows_all_caught_up_message_when_no_topics(self):
        html = fg.generate_html(
            "A01234567", {"name": "Rafael R.", "topics_to_review": []}, "img-src"
        )
        assert "you're all caught up" in html
        assert 'class="section-item"' not in html

    def test_embeds_mascot_image_source(self):
        html = fg.generate_html(
            "A01234567",
            {"name": "Rafael R.", "topics_to_review": []},
            "data:image/png;base64,ABC123",
        )
        assert '<img src="data:image/png;base64,ABC123" class="mascot-img"' in html

    def test_unknown_topic_code_falls_back_to_raw_code(self):
        html = fg.generate_html(
            "A01234567",
            {"name": "Rafael R.", "topics_to_review": ["9.9"]},
            "img-src",
        )
        assert "<li class=\"section-item\">9.9</li>" in html


# ---------------------------------------------------------------------------
# generate_class_report_html
# ---------------------------------------------------------------------------

class TestGenerateClassReportHtml:
    def test_shows_average_and_total_students(self):
        html = fg.generate_class_report_html({"average": 72.5, "missed_topics": []}, 10)
        assert "72.5%" in html
        assert ">10<" in html

    def test_top_three_focus_cards_rendered_for_nonzero_counts(self):
        class_data = {
            "average": 50.0,
            "missed_topics": [("2.1", 8), ("2.3", 5), ("2.5", 2), ("2.7", 1)],
        }
        html = fg.generate_class_report_html(class_data, 20)
        # only the top 3 entries should appear as focus cards
        assert html.count('class="focus-card"') == 3
        assert TOPIC_MAP["2.1"] in html
        assert TOPIC_MAP["2.3"] in html
        assert TOPIC_MAP["2.5"] in html

    def test_top_three_skips_zero_count_topics(self):
        class_data = {"average": 90.0, "missed_topics": [("2.1", 0), ("2.2", 0)]}
        html = fg.generate_class_report_html(class_data, 5)
        assert html.count('class="focus-card"') == 0
        assert "Great job! No topics were missed" in html

    def test_no_focus_message_when_missed_topics_empty(self):
        html = fg.generate_class_report_html({"average": 100.0, "missed_topics": []}, 5)
        assert "Great job! No topics were missed" in html

    def test_bar_widths_scale_relative_to_max_and_avoid_div_by_zero(self):
        # max_missed = 4; bar widths should be percentages of that max
        class_data = {"average": 50.0, "missed_topics": [("2.1", 4), ("2.2", 2), ("2.3", 0)]}
        html = fg.generate_class_report_html(class_data, 10)
        assert "width: 100%;" in html  # 4/4
        assert "width: 50%;" in html  # 2/4
        assert "width: 0%;" in html  # 0/4

    def test_bar_color_classes_assigned_correctly(self):
        # max_missed = 10 -> "high" threshold is count >= 7
        class_data = {"average": 50.0, "missed_topics": [("2.1", 10), ("2.2", 4), ("2.3", 0)]}
        html = fg.generate_class_report_html(class_data, 10)
        assert "bar-fill bar-high" in html
        assert "bar-fill bar-med" in html
        assert "bar-fill bar-zero" in html

    def test_does_not_crash_when_all_missed_counts_are_zero(self):
        # max_missed would be 0 -> must fall back to 1 to avoid ZeroDivisionError
        class_data = {"average": 100.0, "missed_topics": [("2.1", 0), ("2.2", 0)]}
        html = fg.generate_class_report_html(class_data, 5)
        assert "width: 0%;" in html

    def test_unknown_topic_code_gets_generic_title(self):
        class_data = {"average": 40.0, "missed_topics": [("9.9", 3)]}
        html = fg.generate_class_report_html(class_data, 5)
        assert "Topic 9.9" in html


# ---------------------------------------------------------------------------
# file_generator_sync
# ---------------------------------------------------------------------------

class TestFileGeneratorSyncNoMerge:
    def test_zip_contains_summary_and_one_pdf_per_student(
        self, monkeypatch, patched_image, patched_pypdf
    ):
        results = make_results(2)
        pdf_bytes_sequence = [b"summary-pdf", b"student1-pdf", b"student2-pdf"]
        page = FakePage(pdf_bytes_sequence)
        install_fake_playwright(monkeypatch, page)

        zip_buffer = fg.file_generator_sync(
            results, "out.zip", make_class_data(),
            concatenate_files=False, print_ready=False,
        )

        names = zip_names(zip_buffer)
        assert "00_Class_Summary_Report.pdf" in names
        assert "Student1_T._A01000001_review.pdf" in names
        assert "Student2_T._A01000002_review.pdf" in names
        assert len(names) == 3
        # No merging should happen without concatenate_files/print_ready
        assert not any("Merged" in n for n in names)

    def test_filenames_sanitize_spaces_and_slashes(
        self, monkeypatch, patched_image, patched_pypdf
    ):
        results = {
            "A0/123 456": {"name": "Jo/Ann Doe", "score": "10%", "topics_to_review": []}
        }
        page = FakePage([b"summary-pdf", b"student-pdf"])
        install_fake_playwright(monkeypatch, page)

        zip_buffer = fg.file_generator_sync(
            results, "out.zip", make_class_data(), concatenate_files=False, print_ready=False
        )
        names = zip_names(zip_buffer)
        assert "Jo_Ann_Doe_A0_123_456_review.pdf" in names

    def test_zero_students_still_produces_summary_only(
        self, monkeypatch, patched_image, patched_pypdf
    ):
        page = FakePage([b"summary-pdf"])
        install_fake_playwright(monkeypatch, page)

        zip_buffer = fg.file_generator_sync(
            {}, "out.zip", make_class_data(), concatenate_files=False, print_ready=False
        )
        names = zip_names(zip_buffer)
        assert names == ["00_Class_Summary_Report.pdf"]

    def test_browser_launched_headless_and_closed(
        self, monkeypatch, patched_image, patched_pypdf
    ):
        page = FakePage([b"summary-pdf", b"student1-pdf"])
        browser, chromium = install_fake_playwright(monkeypatch, page)

        fg.file_generator_sync(
            make_results(1), "out.zip", make_class_data(),
            concatenate_files=False, print_ready=False,
        )

        assert chromium.launch_kwargs["headless"] is True
        assert page.closed is True
        assert browser.closed is True

    def test_mascot_image_fetched_once_from_expected_url(
        self, monkeypatch, patched_pypdf
    ):
        calls = []
        monkeypatch.setattr(
            fg, "get_image_base64", lambda url: calls.append(url) or "data:fake"
        )
        page = FakePage([b"summary-pdf", b"student1-pdf"])
        install_fake_playwright(monkeypatch, page)

        fg.file_generator_sync(
            make_results(1), "out.zip", make_class_data(),
            concatenate_files=False, print_ready=False,
        )
        assert calls == [fg.MASCOT_IMAGE_URL]


class TestFileGeneratorSyncMerging:
    def test_concatenate_files_writes_single_merged_pdf_and_no_individual_files(
        self, monkeypatch, patched_image, patched_pypdf
    ):
        results = make_results(2)
        page = FakePage([b"summary-pdf", b"student1-pdf", b"student2-pdf"])
        install_fake_playwright(monkeypatch, page)
        FakePdfReader.page_count_queue = [1, 1, 1]  # summary, student1, student2

        zip_buffer = fg.file_generator_sync(
            results, "out.zip", make_class_data(),
            concatenate_files=True, print_ready=False,
        )
        names = zip_names(zip_buffer)
        assert names == ["00_All_Students_Merged.pdf"]

    def test_print_ready_writes_print_ready_filename(
        self, monkeypatch, patched_image, patched_pypdf
    ):
        results = make_results(1)
        page = FakePage([b"summary-pdf", b"student1-pdf"])
        install_fake_playwright(monkeypatch, page)
        FakePdfReader.page_count_queue = [2, 2]  # both already even

        zip_buffer = fg.file_generator_sync(
            results, "out.zip", make_class_data(),
            concatenate_files=False, print_ready=True,
        )
        names = zip_names(zip_buffer)
        assert names == ["00_Print_Ready_Merged.pdf"]

    def test_print_ready_inserts_blank_page_for_odd_page_documents(
        self, monkeypatch, patched_image, patched_pypdf
    ):
        results = make_results(1)
        page = FakePage([b"summary-pdf", b"student1-pdf"])
        install_fake_playwright(monkeypatch, page)
        # summary has 3 pages (odd -> needs a blank), student has 2 (even -> no blank)
        FakePdfReader.page_count_queue = [3, 2]

        captured_writer = {}
        original_writer_cls = FakePdfWriter

        def writer_factory():
            w = original_writer_cls()
            captured_writer["writer"] = w
            return w

        monkeypatch.setattr(fg, "PdfWriter", writer_factory)

        fg.file_generator_sync(
            results, "out.zip", make_class_data(),
            concatenate_files=False, print_ready=True,
        )

        writer = captured_writer["writer"]
        # 3 real summary pages + 1 blank + 2 real student pages = 6 total add_page calls
        assert len(writer.added_pages) == 6
        blank_pages = [p for p in writer.added_pages if getattr(p, "is_blank", False)]
        assert len(blank_pages) == 1

    def test_print_ready_skips_blank_page_when_already_even(
        self, monkeypatch, patched_image, patched_pypdf
    ):
        results = make_results(1)
        page = FakePage([b"summary-pdf", b"student1-pdf"])
        install_fake_playwright(monkeypatch, page)
        FakePdfReader.page_count_queue = [4, 2]  # both even -> no blanks needed

        captured_writer = {}

        def writer_factory():
            w = FakePdfWriter()
            captured_writer["writer"] = w
            return w

        monkeypatch.setattr(fg, "PdfWriter", writer_factory)

        fg.file_generator_sync(
            results, "out.zip", make_class_data(),
            concatenate_files=False, print_ready=True,
        )

        writer = captured_writer["writer"]
        blank_pages = [p for p in writer.added_pages if getattr(p, "is_blank", False)]
        assert len(blank_pages) == 0
        assert len(writer.added_pages) == 6  # 4 + 2, no blanks

    def test_merger_closed_after_write(self, monkeypatch, patched_image, patched_pypdf):
        results = make_results(1)
        page = FakePage([b"summary-pdf", b"student1-pdf"])
        install_fake_playwright(monkeypatch, page)
        FakePdfReader.page_count_queue = [1, 1]

        captured_writer = {}

        def writer_factory():
            w = FakePdfWriter()
            captured_writer["writer"] = w
            return w

        monkeypatch.setattr(fg, "PdfWriter", writer_factory)

        fg.file_generator_sync(
            results, "out.zip", make_class_data(),
            concatenate_files=True, print_ready=False,
        )
        assert captured_writer["writer"].closed is True


class TestFileGeneratorSyncGarbageCollection:
    def test_gc_collect_called_once_per_student(
        self, monkeypatch, patched_image, patched_pypdf
    ):
        results = make_results(3)
        page = FakePage([b"summary-pdf", b"s1", b"s2", b"s3"])
        install_fake_playwright(monkeypatch, page)

        gc_calls = {"count": 0}

        def fake_collect():
            gc_calls["count"] += 1

        monkeypatch.setattr(fg.gc, "collect", fake_collect)

        fg.file_generator_sync(
            results, "out.zip", make_class_data(),
            concatenate_files=False, print_ready=False,
        )
        assert gc_calls["count"] == 3
