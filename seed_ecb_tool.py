"""Simple local SEED-128 ECB text encryptor/decryptor.

Run without arguments for the desktop window. The optional CLI still supports
streaming files for users who explicitly invoke it from a terminal.
"""

from __future__ import annotations

import argparse
import getpass
import os
import queue
import sys
import tempfile
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from seed_ecb_core import decode_value, encode_value, parse_key, transform_bytes, transform_stream

FORMAT_LABELS = {"utf8": "문자열 (UTF-8)", "hex": "Hex", "base64": "Base64"}
PADDING_LABELS = {"pkcs7": "PKCS#7 (기본)", "none": "없음 (16바이트 배수)", "zero": "0x00 채우기"}


def selected_value(label: str, choices: dict[str, str]) -> str:
    for value, display in choices.items():
        if label == display:
            return value
    raise ValueError("선택한 형식을 확인하세요.")


def convert_file(source_path: Path, destination_path: Path, key: bytes, *, decrypt: bool, padding: str, progress=None) -> tuple[int, int]:
    """Write a CLI result to a temporary file, replacing output on success."""
    if source_path.resolve() == destination_path.resolve():
        raise ValueError("원본 파일과 저장할 파일은 서로 달라야 합니다.")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with source_path.open("rb") as source, tempfile.NamedTemporaryFile(
            mode="wb", prefix=f".{destination_path.name}.", suffix=".part", dir=destination_path.parent, delete=False
        ) as destination:
            temporary = Path(destination.name)
            counts = transform_stream(source, destination, key, decrypt=decrypt, padding=padding, progress=progress)
        os.replace(temporary, destination_path)
        temporary = None
        return counts
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class SeedWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SEED-ECB 암복호화")
        self.root.geometry("980x700")
        self.root.minsize(760, 560)
        self.mode = tk.StringVar(value="encrypt")
        self.key_format = tk.StringVar(value=FORMAT_LABELS["utf8"])
        self.key_text = tk.StringVar()
        self.padding = tk.StringVar(value=PADDING_LABELS["pkcs7"])
        self.input_format = tk.StringVar(value=FORMAT_LABELS["utf8"])
        self.output_format = tk.StringVar(value=FORMAT_LABELS["base64"])
        self.result_bytes: bytes | None = None
        self.messages: queue.Queue[tuple] = queue.Queue()
        self.running = False
        self._build()
        self._update_mode()
        self._update_key_count()
        self.root.after(80, self._poll)

    def _build(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Malgun Gothic", 19, "bold"))
        style.configure("Section.TLabel", font=("Malgun Gothic", 11, "bold"))
        style.configure("Hint.TLabel", foreground="#607188")

        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        heading = ttk.Frame(main)
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(heading, text="SEED-ECB 암복호화", style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, text="긴 문자열도 입력할 수 있습니다.", style="Hint.TLabel").pack(anchor="w")

        settings = ttk.LabelFrame(main, text="방식과 키", padding=10)
        settings.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        settings.columnconfigure(4, weight=1)
        ttk.Radiobutton(settings, text="암호화", value="encrypt", variable=self.mode, command=self._update_mode).grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Radiobutton(settings, text="복호화", value="decrypt", variable=self.mode, command=self._update_mode).grid(row=0, column=1, sticky="w", padx=(0, 16))
        ttk.Label(settings, text="키 형식").grid(row=0, column=2, sticky="e", padx=(0, 5))
        self.key_format_box = ttk.Combobox(settings, textvariable=self.key_format, state="readonly", width=16, values=list(FORMAT_LABELS.values()))
        self.key_format_box.grid(row=0, column=3, sticky="w")
        ttk.Label(settings, text="패딩").grid(row=0, column=4, sticky="e", padx=(12, 5))
        self.padding_box = ttk.Combobox(settings, textvariable=self.padding, state="readonly", width=22, values=list(PADDING_LABELS.values()))
        self.padding_box.grid(row=0, column=5, sticky="w")
        ttk.Label(settings, text="비밀키").grid(row=1, column=0, sticky="w", pady=(9, 0))
        self.key_entry = ttk.Entry(settings, textvariable=self.key_text, show="●")
        self.key_entry.grid(row=1, column=1, columnspan=4, sticky="ew", pady=(9, 0), padx=(0, 7))
        self.show_button = ttk.Button(settings, text="표시", width=6, command=self._toggle_key)
        self.show_button.grid(row=1, column=5, sticky="e", pady=(9, 0))
        self.key_count = ttk.Label(settings, style="Hint.TLabel")
        self.key_count.grid(row=2, column=1, columnspan=5, sticky="w", pady=(3, 0))
        self.key_text.trace_add("write", lambda *_: self._update_key_count())
        self.key_format.trace_add("write", lambda *_: self._update_key_count())

        panes = ttk.PanedWindow(main, orient="horizontal")
        panes.grid(row=2, column=0, sticky="nsew")
        left = ttk.Frame(panes, padding=(0, 0, 6, 0))
        right = ttk.Frame(panes, padding=(6, 0, 0, 0))
        panes.add(left, weight=1)
        panes.add(right, weight=1)
        for pane in (left, right):
            pane.columnconfigure(0, weight=1)
            pane.rowconfigure(2, weight=1)
        ttk.Label(left, text="입력", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.input_format_box = ttk.Combobox(left, textvariable=self.input_format, state="readonly", width=20)
        self.input_format_box.grid(row=1, column=0, sticky="w", pady=(4, 6))
        self.input_text = scrolledtext.ScrolledText(left, wrap="word", font=("Consolas", 10), undo=True)
        self.input_text.grid(row=2, column=0, sticky="nsew")
        ttk.Label(right, text="결과", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.output_format_box = ttk.Combobox(right, textvariable=self.output_format, state="readonly", width=20)
        self.output_format_box.grid(row=1, column=0, sticky="w", pady=(4, 6))
        self.output_format_box.bind("<<ComboboxSelected>>", lambda _: self._render_result())
        self.output_text = scrolledtext.ScrolledText(right, wrap="word", font=("Consolas", 10), state="disabled")
        self.output_text.grid(row=2, column=0, sticky="nsew")

        actions = ttk.Frame(main)
        actions.grid(row=3, column=0, sticky="ew", pady=(10, 2))
        self.run_button = ttk.Button(actions, text="암호화하기", command=self._start)
        self.run_button.pack(side="left")
        self.status = ttk.Label(actions, text="", style="Hint.TLabel")
        self.status.pack(side="left", padx=10)
        ttk.Label(main, text="SEED 키는 16바이트입니다. 기존 암호문을 다룰 때는 키와 패딩을 맞추세요.", style="Hint.TLabel", wraplength=940).grid(row=4, column=0, sticky="w", pady=(8, 0))

    def _set_output(self, value: str) -> None:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", value)
        self.output_text.configure(state="disabled")

    def _update_mode(self) -> None:
        if self.mode.get() == "encrypt":
            self.input_format_box.configure(values=tuple(FORMAT_LABELS[x] for x in ("utf8", "hex", "base64")))
            self.output_format_box.configure(values=tuple(FORMAT_LABELS[x] for x in ("base64", "hex")))
            self.input_format.set(FORMAT_LABELS["utf8"])
            self.output_format.set(FORMAT_LABELS["base64"])
            self.run_button.configure(text="암호화하기")
        else:
            self.input_format_box.configure(values=tuple(FORMAT_LABELS[x] for x in ("base64", "hex")))
            self.output_format_box.configure(values=tuple(FORMAT_LABELS[x] for x in ("utf8", "hex", "base64")))
            self.input_format.set(FORMAT_LABELS["base64"])
            self.output_format.set(FORMAT_LABELS["utf8"])
            self.run_button.configure(text="복호화하기")
        self.result_bytes = None
        self._set_output("")

    def _update_key_count(self) -> None:
        try:
            count = len(decode_value(self.key_text.get(), selected_value(self.key_format.get(), FORMAT_LABELS)))
            self.key_count.configure(text=f"현재 {count}바이트 / 필요한 길이 16바이트")
        except ValueError as exc:
            self.key_count.configure(text=str(exc))

    def _toggle_key(self) -> None:
        visible = self.key_entry.cget("show") == ""
        self.key_entry.configure(show="●" if visible else "")
        self.show_button.configure(text="표시" if visible else "숨기기")

    def _start(self) -> None:
        if self.running:
            return
        try:
            key = parse_key(self.key_text.get(), selected_value(self.key_format.get(), FORMAT_LABELS))
            text = self.input_text.get("1.0", "end-1c")
            if not text:
                raise ValueError("내용을 입력하세요.")
            input_format = selected_value(self.input_format.get(), FORMAT_LABELS)
        except ValueError as exc:
            messagebox.showerror("입력 확인", str(exc))
            return
        self.result_bytes = None
        self._set_output("")
        self.status.configure(text="처리 중…")
        self.running = True
        self.run_button.configure(state="disabled")
        threading.Thread(
            target=self._worker,
            args=(key, self.mode.get() == "decrypt", selected_value(self.padding.get(), PADDING_LABELS), text, input_format),
            daemon=True,
        ).start()

    def _worker(self, key: bytes, decrypt: bool, padding: str, text: str, input_format: str) -> None:
        try:
            data = decode_value(text, input_format)
            result = transform_bytes(data, key, decrypt=decrypt, padding=padding)
            self.messages.put(("complete", result, len(data)))
        except Exception as exc:
            self.messages.put(("error", str(exc)))

    def _poll(self) -> None:
        try:
            while True:
                event = self.messages.get_nowait()
                self.running = False
                self.run_button.configure(state="normal")
                if event[0] == "complete":
                    self.result_bytes = event[1]
                    self.status.configure(text=f"완료 · {event[2]:,} → {len(self.result_bytes):,}바이트")
                    self._render_result()
                else:
                    self.status.configure(text="처리하지 못했습니다.")
                    messagebox.showerror("처리 실패", event[1])
        except queue.Empty:
            pass
        self.root.after(80, self._poll)

    def _render_result(self) -> None:
        if self.result_bytes is None:
            return
        try:
            result = encode_value(self.result_bytes, selected_value(self.output_format.get(), FORMAT_LABELS))
            self._set_output(result)
        except ValueError as exc:
            self._set_output("")
            self.status.configure(text=str(exc))


def cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="SEED-128 ECB 파일 암복호화. 키는 실행 시 별도로 입력합니다.")
    parser.add_argument("operation", choices=("encrypt", "decrypt"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--key-format", choices=("utf8", "hex", "base64"), default="utf8")
    parser.add_argument("--padding", choices=("pkcs7", "none", "zero"), default="pkcs7")
    parser.add_argument("--overwrite", action="store_true", help="기존 출력 파일 덮어쓰기")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.overwrite:
        parser.error("출력 파일이 이미 있습니다. 다른 이름이나 --overwrite를 지정하세요.")
    try:
        key = parse_key(getpass.getpass("SEED 키: "), args.key_format)
        read_count, written_count = convert_file(
            args.input, args.output, key, decrypt=args.operation == "decrypt", padding=args.padding
        )
        print(f"완료: {read_count:,} → {written_count:,}바이트 · {args.output}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        raise SystemExit(cli(sys.argv[2:]))
    root = tk.Tk()
    SeedWindow(root)
    root.mainloop()
