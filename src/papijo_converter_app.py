from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from papijo_converter import APP_VERSION, LIBRARIES, PAPIJO_DESTINATION_WARNING, convert_file, find_h5p_files


class ConverterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"H5P Convert to Papi Jo {APP_VERSION}")
        self.geometry("860x650")
        self.minsize(760, 560)

        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.confirm_warning = tk.BooleanVar(value=False)
        self.library_vars = {machine: tk.BooleanVar(value=True) for machine in LIBRARIES}
        self.results_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)

        title = ttk.Label(root, text="Convert H5P content to Papi Jo", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, sticky="w")

        warning = ttk.Label(
            root,
            text=PAPIJO_DESTINATION_WARNING,
            wraplength=790,
            foreground="#7a3b00",
            padding=(0, 8, 0, 8),
        )
        warning.grid(row=1, column=0, sticky="ew")

        paths = ttk.LabelFrame(root, text="Folders", padding=12)
        paths.grid(row=2, column=0, sticky="ew", pady=(4, 12))
        paths.columnconfigure(1, weight=1)

        ttk.Label(paths, text="Input folder").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(paths, textvariable=self.input_folder).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(paths, text="Browse...", command=self._choose_input).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(paths, text="Output folder").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(paths, textvariable=self.output_folder).grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(paths, text="Browse...", command=self._choose_output).grid(row=1, column=2, padx=(8, 0), pady=4)

        libraries = ttk.LabelFrame(root, text="Libraries to convert", padding=12)
        libraries.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        library_actions = ttk.Frame(libraries)
        library_actions.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Button(library_actions, text="Check all", command=self._check_all_libraries).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(library_actions, text="Check none", command=self._check_no_libraries).grid(row=0, column=1)
        for index, (machine, rule) in enumerate(LIBRARIES.items()):
            checkbox = ttk.Checkbutton(libraries, text=rule.display_label, variable=self.library_vars[machine])
            checkbox.grid(row=(index // 2) + 1, column=index % 2, sticky="w", padx=(0, 24), pady=2)

        output = ttk.LabelFrame(root, text="Conversion log", padding=12)
        output.grid(row=4, column=0, sticky="nsew")
        output.columnconfigure(0, weight=1)
        output.rowconfigure(0, weight=1)
        self.log = tk.Text(output, height=12, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(output, orient=tk.VERTICAL, command=self.log.yview)
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        footer = ttk.Frame(root)
        footer.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Checkbutton(
            footer,
            text="I understand that the destination H5P platform must already have the Papi Jo libraries installed.",
            variable=self.confirm_warning,
        ).grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.grid(row=1, column=0, sticky="ew", pady=(10, 0), padx=(0, 12))
        self.convert_button = ttk.Button(footer, text="Check and convert files", command=self._start_conversion)
        self.convert_button.grid(row=1, column=1, sticky="e", pady=(10, 0))

    def _choose_input(self) -> None:
        folder = filedialog.askdirectory(title="Select folder containing .h5p files")
        if folder:
            self.input_folder.set(folder)
            if not self.output_folder.get():
                self.output_folder.set(str(Path(folder) / "papijo-converted"))

    def _check_all_libraries(self) -> None:
        for variable in self.library_vars.values():
            variable.set(True)

    def _check_no_libraries(self) -> None:
        for variable in self.library_vars.values():
            variable.set(False)

    def _choose_output(self) -> None:
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_folder.set(folder)

    def _start_conversion(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        if not self.confirm_warning.get():
            messagebox.showwarning("Papi Jo libraries required", PAPIJO_DESTINATION_WARNING)
            return

        input_folder = Path(self.input_folder.get())
        output_folder = Path(self.output_folder.get())
        selected = {machine for machine, var in self.library_vars.items() if var.get()}

        if not input_folder.is_dir():
            messagebox.showerror("Input folder required", "Select a folder containing exported .h5p files.")
            return
        if not selected:
            messagebox.showerror("Library selection required", "Choose at least one supported library.")
            return

        files = find_h5p_files(input_folder)
        if not files:
            messagebox.showwarning("No H5P files", "Cannot find any .h5p files in the selected folder.")
            return

        self.progress.configure(value=0, maximum=len(files))
        self.convert_button.configure(state=tk.DISABLED)
        self._clear_log()
        self._log(f"Found {len(files)} .h5p file(s). Starting conversion...\n")

        self.worker = threading.Thread(
            target=self._convert_worker,
            args=(files, output_folder, selected),
            daemon=True,
        )
        self.worker.start()
        self.after(100, self._poll_results)

    def _convert_worker(self, files: list[Path], output_folder: Path, selected: set[str]) -> None:
        converted = 0
        output_folder.mkdir(parents=True, exist_ok=True)
        for index, source in enumerate(files, start=1):
            result = convert_file(source, output_folder, selected)
            converted += int(result.converted)
            self.results_queue.put(("result", (index, result)))
        self.results_queue.put(("done", (converted, len(files), output_folder)))

    def _poll_results(self) -> None:
        while True:
            try:
                event, payload = self.results_queue.get_nowait()
            except queue.Empty:
                break

            if event == "result":
                index, result = payload
                self.progress.configure(value=index)
                if result.converted:
                    self._log(f"OK: {result.source.name} -> {result.output.name}: {result.message}\n")
                else:
                    self._log(f"WARNING: {result.source.name}: {result.message}\n")
            elif event == "done":
                converted, total, output_folder = payload
                if converted:
                    self._log(f"\nConverted {converted} of {total} file(s).\nOutput folder: {output_folder}\n")
                    messagebox.showinfo("Conversion complete", f"Converted {converted} of {total} file(s).")
                else:
                    self._log(
                        "\nCannot find any H5P file which can be converted to a Papi Jo version in the selected folder.\n"
                    )
                    messagebox.showwarning("No convertible files", "No selected H5P file could be converted.")
                self.convert_button.configure(state=tk.NORMAL)
                return

        if self.worker and self.worker.is_alive():
            self.after(100, self._poll_results)
        else:
            self.convert_button.configure(state=tk.NORMAL)

    def _log(self, message: str) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, message)
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.delete("1.0", tk.END)
        self.log.configure(state=tk.DISABLED)


def main() -> None:
    app = ConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
