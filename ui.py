# ui.py
import sys
from pathlib import Path

import requests
from tqdm import tqdm

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QPlainTextEdit,
    QProgressBar,
    QMessageBox,
    QFormLayout,
    QSizePolicy,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QGroupBox,
    QTabWidget,
    QSplitter,
)

import core


class WorkflowWorker(QThread):
    progress = pyqtSignal(int, int)       # current_index, total
    log = pyqtSignal(str)                 # log message
    finished = pyqtSignal(int, int)       # processed_count, failed_count
    discovered = pyqtSignal(int)          # total files discovered

    def __init__(
        self,
        files,
        base_input: Path,
        output_root: Path,
        model: str,
        host: str,
        num_predict,
        temperature,
        top_p,
        num_ctx,
        repeat_penalty,
        system_prompt: str,
        user_prompt_template: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.files = files
        self.base_input = base_input
        self.output_root = output_root
        self.model = model
        self.host = host
        self.num_predict = num_predict
        self.temperature = temperature
        self.top_p = top_p
        self.num_ctx = num_ctx
        self.repeat_penalty = repeat_penalty
        self.system_prompt = system_prompt
        self.user_prompt_template = user_prompt_template

    def run(self) -> None:
        core.logger.setLevel(core.logging.INFO)

        self.log.emit(f"Output directory: {self.output_root}")
        self.log.emit(f"Model: {self.model}")
        self.log.emit(f"Host: {self.host}")
        self.log.emit(
            "LLM settings: "
            f"num_predict={self.num_predict}, "
            f"temperature={self.temperature}, "
            f"top_p={self.top_p}, "
            f"num_ctx={self.num_ctx}, "
            f"repeat_penalty={self.repeat_penalty}"
        )

        total = len(self.files)
        self.discovered.emit(total)

        if total == 0:
            self.log.emit("No JSON workflow files selected.")
            self.finished.emit(0, 0)
            return

        processed_count = 0
        failed_count = 0

        pbar = tqdm(total=total, desc="Processing workflows", unit="file")

        for idx, p in enumerate(self.files, start=1):
            if self.isInterruptionRequested():
                self.log.emit("Interrupted by user; stopping.")
                break

            self.log.emit(f"Processing file {idx}/{total}: {p}")
            try:
                success = core.process_workflow_file(
                    path=p,
                    output_root=self.output_root,
                    base_input=self.base_input,
                    model=self.model,
                    host=self.host,
                    dry_run=False,
                    num_predict=self.num_predict,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    num_ctx=self.num_ctx,
                    repeat_penalty=self.repeat_penalty,
                    system_prompt=self.system_prompt,
                    user_prompt_template=self.user_prompt_template,
                )
                if success:
                    processed_count += 1
                else:
                    failed_count += 1
            except Exception as exc:
                failed_count += 1
                self.log.emit(f"Exception while processing {p}: {exc!r}")

            pbar.update(1)
            self.log.emit(str(pbar))
            self.progress.emit(idx, total)

        pbar.close()
        self.log.emit("Processing complete.")
        self.finished.emit(processed_count, failed_count)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("n8n-DocGen")
        self.resize(1200, 800)

        self.worker = None
        self.input_path: Path | None = None

        # Load base config
        self.config = core.load_config()

        central = QWidget()
        self.setCentralWidget(central)

        outer_layout = QVBoxLayout()
        central.setLayout(outer_layout)

        splitter = QSplitter(Qt.Orientation.Vertical)
        outer_layout.addWidget(splitter)

        # Top area: tabs for Workflows / LLM / Prompts
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        top_widget.setLayout(top_layout)

        self.tabs = QTabWidget()
        top_layout.addWidget(self.tabs)

        # Workflows tab
        self.workflows_tab = QWidget()
        self._build_workflows_tab()
        self.tabs.addTab(self.workflows_tab, "Workflows")

        # LLM & Models tab
        self.llm_tab = QWidget()
        self._build_llm_tab()
        self.tabs.addTab(self.llm_tab, "LLM & Models")

        # Prompts tab
        self.prompts_tab = QWidget()
        self._build_prompts_tab()
        self.tabs.addTab(self.prompts_tab, "Prompts")

        splitter.addWidget(top_widget)

        # Bottom area: logs and progress
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()
        bottom_widget.setLayout(bottom_layout)

        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        self.status_label = QLabel("Ready.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        bottom_layout.addLayout(progress_layout)

        self.log_widget = QPlainTextEdit()
        self.log_widget.setReadOnly(True)
        self.log_widget.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.log_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        bottom_layout.addWidget(self.log_widget)

        splitter.addWidget(bottom_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        self._load_initial_config()
        self._refresh_models()

    # Workflows tab
    def _build_workflows_tab(self) -> None:
        layout = QVBoxLayout()
        self.workflows_tab.setLayout(layout)

        form = QFormLayout()

        self.input_path_edit = QLineEdit()
        self.input_path_edit.setPlaceholderText("Path to JSON file or directory...")
        input_browse_btn = QPushButton("Browse")
        input_browse_btn.clicked.connect(self.browse_input)
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_path_edit)
        input_layout.addWidget(input_browse_btn)
        form.addRow("Input path:", input_layout)

        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setText("generated")
        output_browse_btn = QPushButton("Browse")
        output_browse_btn.clicked.connect(self.browse_output)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(output_browse_btn)
        form.addRow("Output directory:", output_layout)

        layout.addLayout(form)

        workflows_group = QGroupBox("Loaded JSON workflows")
        workflows_layout = QVBoxLayout()
        self.load_workflows_btn = QPushButton("Load workflows from input path")
        self.load_workflows_btn.clicked.connect(self.load_workflows)
        self.workflow_list = QListWidget()
        self.workflow_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        workflows_layout.addWidget(self.load_workflows_btn)
        workflows_layout.addWidget(self.workflow_list)
        workflows_group.setLayout(workflows_layout)
        layout.addWidget(workflows_group)

        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Generate docs for selected")
        self.start_btn.clicked.connect(self.start_processing)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_processing)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    # LLM & models tab
    def _build_llm_tab(self) -> None:
        layout = QVBoxLayout()
        self.llm_tab.setLayout(layout)

        form = QFormLayout()

        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("http://localhost:11434")
        form.addRow("Ollama host:", self.host_edit)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(False)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        refresh_models_btn = QPushButton("Refresh models")
        refresh_models_btn.clicked.connect(self._refresh_models)
        model_layout = QHBoxLayout()
        model_layout.addWidget(self.model_combo)
        model_layout.addWidget(refresh_models_btn)
        form.addRow("Ollama model:", model_layout)

        self.temperature_edit = QLineEdit()
        self.temperature_edit.setPlaceholderText("e.g. 0.2 (empty = default)")

        self.top_p_edit = QLineEdit()
        self.top_p_edit.setPlaceholderText("e.g. 0.9 (empty = default)")

        self.num_predict_edit = QLineEdit()
        self.num_predict_edit.setPlaceholderText("Max tokens to generate (num_predict)")

        self.num_ctx_edit = QLineEdit()
        self.num_ctx_edit.setPlaceholderText("Context window size (num_ctx)")

        self.repeat_penalty_edit = QLineEdit()
        self.repeat_penalty_edit.setPlaceholderText("e.g. 1.1 (empty = default)")

        form.addRow("Temperature:", self.temperature_edit)
        form.addRow("Top-p:", self.top_p_edit)
        form.addRow("Max tokens:", self.num_predict_edit)
        form.addRow("Context tokens:", self.num_ctx_edit)
        form.addRow("Repeat penalty:", self.repeat_penalty_edit)

        layout.addLayout(form)
        layout.addStretch()

    # Prompts tab
    def _build_prompts_tab(self) -> None:
        layout = QVBoxLayout()
        self.prompts_tab.setLayout(layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        sys_group = QGroupBox("System prompt")
        sys_layout = QVBoxLayout()
        self.system_prompt_edit = QPlainTextEdit()
        self.system_prompt_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        sys_layout.addWidget(self.system_prompt_edit)
        sys_group.setLayout(sys_layout)

        usr_group = QGroupBox("User prompt template")
        usr_layout = QVBoxLayout()
        self.user_prompt_edit = QPlainTextEdit()
        self.user_prompt_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        usr_layout.addWidget(self.user_prompt_edit)
        usr_group.setLayout(usr_layout)

        splitter.addWidget(sys_group)
        splitter.addWidget(usr_group)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

    def _load_initial_config(self) -> None:
        host = self.config.get("host", "http://localhost:11434")
        model = self.config.get("model", core.DEFAULT_OLLAMA_MODEL)
        num_predict = self.config.get("num_predict")
        temperature = self.config.get("temperature")
        top_p = self.config.get("top_p")
        num_ctx = self.config.get("num_ctx")
        repeat_penalty = self.config.get("repeat_penalty")
        system_prompt = self.config.get("system_prompt", core.SYSTEM_PROMPT)
        user_prompt_template = self.config.get("user_prompt_template", core.USER_PROMPT_TEMPLATE)

        self.host_edit.setText(host)
        self.system_prompt_edit.setPlainText(system_prompt)
        self.user_prompt_edit.setPlainText(user_prompt_template)

        if num_predict is not None:
            self.num_predict_edit.setText(str(num_predict))
        if temperature is not None:
            self.temperature_edit.setText(str(temperature))
        if top_p is not None:
            self.top_p_edit.setText(str(top_p))
        if num_ctx is not None:
            self.num_ctx_edit.setText(str(num_ctx))
        if repeat_penalty is not None:
            self.repeat_penalty_edit.setText(str(repeat_penalty))

    def append_log(self, text: str) -> None:
        self.log_widget.appendPlainText(text)
        cursor = self.log_widget.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.log_widget.setTextCursor(cursor)

    def browse_input(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select workflow directory")
        if directory:
            self.input_path_edit.setText(directory)
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select workflow JSON file",
            "",
            "JSON files (*.json);;All files (*.*)",
        )
        if file_path:
            self.input_path_edit.setText(file_path)

    def browse_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select output directory")
        if directory:
            self.output_dir_edit.setText(directory)

    def _refresh_models(self) -> None:
        host_str = self.host_edit.text().strip() or "http://localhost:11434"
        url = host_str.rstrip("/") + "/api/tags"

        self.model_combo.clear()
        try:
            self.append_log(f"Querying Ollama models from {url} ...")
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            models = []
            for m in data.get("models", []):
                name = m.get("name")
                if name:
                    models.append(name)

            models = sorted(set(models))
            if not models:
                raise RuntimeError("No models returned from Ollama")

            for name in models:
                self.model_combo.addItem(name)

            default_name = self.config.get("model", core.DEFAULT_OLLAMA_MODEL)
            idx = self.model_combo.findText(default_name)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

            self.append_log(f"Found {len(models)} model(s).")
        except Exception as exc:
            fallback = self.config.get("model", core.DEFAULT_OLLAMA_MODEL)
            self.append_log(f"Failed to fetch models from Ollama: {exc!r}")
            self.append_log(f"Falling back to default model: {fallback}")
            self.model_combo.addItem(fallback)

    def load_workflows(self) -> None:
        input_path_str = self.input_path_edit.text().strip()
        if not input_path_str:
            QMessageBox.warning(self, "Input required", "Please specify an input file or directory.")
            return

        self.input_path = Path(input_path_str).expanduser().resolve()
        if not self.input_path.exists():
            QMessageBox.critical(self, "Invalid input", f"Input path does not exist:\n{self.input_path}")
            return

        json_files = core.find_json_files(self.input_path)
        self.workflow_list.clear()

        if not json_files:
            self.append_log("No JSON workflow files found.")
            self.status_label.setText("No JSON files found.")
            return

        base = self.input_path if self.input_path.is_dir() else self.input_path.parent

        for p in json_files:
            try:
                rel = p.relative_to(base)
                label = str(rel)
            except ValueError:
                label = str(p)

            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.workflow_list.addItem(item)

        self.append_log(f"Loaded {len(json_files)} workflow file(s).")
        self.status_label.setText(f"Loaded {len(json_files)} workflow file(s).")

    def parse_float(self, text: str):
        text = text.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            QMessageBox.warning(self, "Invalid value", f"Invalid float value: {text}")
            return None

    def parse_int(self, text: str):
        text = text.strip()
        if not text:
            return None
        try:
            return int(text)
        except ValueError:
            QMessageBox.warning(self, "Invalid value", f"Invalid integer value: {text}")
            return None

    def collect_selected_files(self):
        files = []
        for i in range(self.workflow_list.count()):
            item = self.workflow_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                p_str = item.data(Qt.ItemDataRole.UserRole)
                if p_str:
                    files.append(Path(p_str))
        return files

    def start_processing(self) -> None:
        input_path_str = self.input_path_edit.text().strip()
        output_dir_str = self.output_dir_edit.text().strip()
        host_str = self.host_edit.text().strip() or "http://localhost:11434"

        if not input_path_str:
            QMessageBox.warning(self, "Input required", "Please specify an input file or directory.")
            return
        if not output_dir_str:
            QMessageBox.warning(self, "Output required", "Please specify an output directory.")
            return

        if self.workflow_list.count() == 0:
            self.load_workflows()
            if self.workflow_list.count() == 0:
                return

        selected_files = self.collect_selected_files()
        if not selected_files:
            QMessageBox.warning(self, "No selection", "Please select at least one workflow to process.")
            return

        input_path = Path(input_path_str).expanduser().resolve()
        base_input = input_path if input_path.is_dir() else input_path.parent
        output_root = Path(output_dir_str).expanduser().resolve()

        if not input_path.exists():
            QMessageBox.critical(self, "Invalid input", f"Input path does not exist:\n{input_path}")
            return

        model_str = self.model_combo.currentText().strip() or self.config.get(
            "model", core.DEFAULT_OLLAMA_MODEL
        )

        temperature = self.parse_float(self.temperature_edit.text())
        if self.temperature_edit.text().strip() and temperature is None:
            return

        top_p = self.parse_float(self.top_p_edit.text())
        if self.top_p_edit.text().strip() and top_p is None:
            return

        num_predict = self.parse_int(self.num_predict_edit.text())
        if self.num_predict_edit.text().strip() and num_predict is None:
            return

        num_ctx = self.parse_int(self.num_ctx_edit.text())
        if self.num_ctx_edit.text().strip() and num_ctx is None:
            return

        repeat_penalty = self.parse_float(self.repeat_penalty_edit.text())
        if self.repeat_penalty_edit.text().strip() and repeat_penalty is None:
            return

        system_prompt = self.system_prompt_edit.toPlainText().strip() or core.SYSTEM_PROMPT
        user_prompt_template = (
            self.user_prompt_edit.toPlainText().strip() or core.USER_PROMPT_TEMPLATE
        )

        self.log_widget.clear()
        self.append_log("Starting documentation generation...")
        total = len(selected_files)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Processing 0/{total}...")

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self.worker = WorkflowWorker(
            files=selected_files,
            base_input=base_input,
            output_root=output_root,
            model=model_str,
            host=host_str,
            num_predict=num_predict,
            temperature=temperature,
            top_p=top_p,
            num_ctx=num_ctx,
            repeat_penalty=repeat_penalty,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
        )

        self.worker.log.connect(self.append_log)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.discovered.connect(self.on_discovered)

        self.worker.start()

    def cancel_processing(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.append_log("Cancellation requested. Current file will finish, then stop.")
            self.worker.requestInterruption()
        self.cancel_btn.setEnabled(False)

    def on_discovered(self, total: int) -> None:
        if total == 0:
            self.progress_bar.setMaximum(1)
            self.progress_bar.setValue(0)
            self.status_label.setText("No JSON files selected.")
        else:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(0)
            self.status_label.setText(f"Found {total} selected workflow file(s).")

    def on_progress(self, current: int, total: int) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"Processing {current}/{total}...")

    def on_finished(self, processed: int, failed: int) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.worker = None

        msg = f"Processing complete. Succeeded: {processed}, Failed: {failed}"
        self.append_log(msg)
        self.status_label.setText(msg)
        QMessageBox.information(self, "Done", msg)


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
