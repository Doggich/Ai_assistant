import customtkinter as ctk
import tkinter as tk
import threading
import speech_recognition as sr
from module.conversation import Conversation
from module.speech_synthesizer import SpeechSynthesizer
import os
import time
import queue


class VoiceAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lumi")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        self.message_queue = queue.Queue()

        self.conversation = Conversation()
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self.is_processing = False  # Флаг обработки запроса
        self.voice_enabled = ctk.BooleanVar(value=False)
        self.speech = SpeechSynthesizer(self.update_status)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme(os.path.join(self.BASE_DIR, "./theme/app_theme.json"))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_context_menu()
        self.create_widgets()

        self.root.after(100, self.process_queue)

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0, activebackground="#748DAE")
        self.context_menu.add_command(
            label="Вырезать",
            command=self.cut_text,
            accelerator="Ctrl+X"
        )
        self.context_menu.add_command(
            label="Копировать",
            command=self.copy_text,
            accelerator="Ctrl+C"
        )
        self.context_menu.add_command(
            label="Вставить",
            command=self.paste_text,
            accelerator="Ctrl+V"
        )

    def show_context_menu(self, event):
        widget = event.widget

        if isinstance(widget, tk.Text):
            has_selection = widget.tag_ranges("sel")
        elif isinstance(widget, tk.Entry):
            has_selection = widget.selection_present()
        else:
            has_selection = False

        # Настраиваем состояние пунктов меню
        self.context_menu.entryconfig("Вырезать", state="normal" if has_selection else "disabled")
        self.context_menu.entryconfig("Копировать", state="normal" if has_selection else "disabled")
        self.context_menu.entryconfig("Вставить", state="normal")

        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def cut_text(self, event=None):
        widget = self.root.focus_get()
        if not widget:
            return

        if isinstance(widget, tk.Text) and widget.tag_ranges("sel"):
            self.copy_text()
            widget.delete("sel.first", "sel.last")
        elif isinstance(widget, tk.Entry) and widget.selection_present():
            self.copy_text()
            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)

    def copy_text(self, event=None):
        widget = self.root.focus_get()
        if not widget:
            return

        if isinstance(widget, tk.Text) and widget.tag_ranges("sel"):
            selected_text = widget.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        elif isinstance(widget, tk.Entry) and widget.selection_present():
            selected_text = widget.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)

    def paste_text(self, event=None):
        widget = self.root.focus_get()
        if not widget:
            return

        clipboard_text = self.root.clipboard_get()
        if isinstance(widget, tk.Text):
            widget.insert(tk.INSERT, clipboard_text)
        elif isinstance(widget, tk.Entry):
            widget.insert(tk.INSERT, clipboard_text)

    def create_widgets(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        control_frame = ctk.CTkFrame(self.root)
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew", columnspan=2)

        self.btn_listen = ctk.CTkButton(
            control_frame,
            text="Старт записи",
            command=self.toggle_listening
        )
        self.btn_listen.pack(side="left", padx=5)

        self.btn_exit = ctk.CTkButton(
            control_frame,
            text="Стоп и выход",
            command=self.on_close
        )
        self.btn_exit.pack(side="left", padx=5)

        self.voice_check = ctk.CTkCheckBox(
            control_frame,
            text="Голосовой ответ",
            variable=self.voice_enabled,
            command=self.toggle_voice
        )
        self.voice_check.pack(side="right", padx=5)

        input_frame = ctk.CTkFrame(self.root)
        input_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew", columnspan=2)

        self.text_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Введите сообщение..."
        )
        self.text_input._entry.configure(
            selectbackground="#748DAE",
            selectforeground="white"
        )
        self.text_input.pack(side="left", fill="x", expand=True, padx=5)
        self.text_input.bind("<Return>", lambda event: self.send_text())
        self.text_input._entry.bind("<Button-3>", self.show_context_menu)

        self.btn_send = ctk.CTkButton(
            input_frame,
            text="Отправить",
            command=self.send_text,
            state="normal"
        )
        self.btn_send.pack(side="left", padx=5)

        # Область диалога
        chat_frame = ctk.CTkFrame(self.root)
        chat_frame.grid(row=1, column=0, padx=(10, 0), pady=5, sticky="nsew")
        chat_frame.grid_columnconfigure(0, weight=1)
        chat_frame.grid_rowconfigure(0, weight=1)

        self.dialogue_area = ctk.CTkTextbox(
            chat_frame,
            wrap="word",
            font=("Consolas", 14),
            activate_scrollbars=False,
            state="disabled"
        )
        self.dialogue_area.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ctk.CTkScrollbar(
            chat_frame,
            orientation="vertical",
            command=self.dialogue_area.yview
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.dialogue_area.configure(yscrollcommand=self.scrollbar.set)

        self.dialogue_area.configure(state="normal")
        self.dialogue_area.tag_config("user", foreground="#4FC3F7")
        self.dialogue_area.tag_config("assistant", foreground="#BA68C8")
        self.dialogue_area.tag_config("error", foreground="#EF5350")
        self.dialogue_area.configure(state="disabled")

        text_widget = self.dialogue_area._textbox
        text_widget.configure(
            exportselection=1,
            selectbackground="#748DAE",
            inactiveselectbackground="#748DAE"
        )
        text_widget.bind("<Button-3>", self.show_context_menu)
        text_widget.bind("<MouseWheel>", self.on_mousewheel)

        self.status_bar = ctk.CTkLabel(
            self.root,
            text="Готов к работе",
            font=("Consolas", 12, "italic"),
            anchor="w",
            corner_radius=0
        )
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=10, pady=5, columnspan=2)

    def on_mousewheel(self, event):
        if event.delta:
            self.dialogue_area.yview("scroll", -1 * (event.delta // 120), "units")
        else:
            if event.num == 4:
                self.dialogue_area.yview("scroll", -1, "units")
            elif event.num == 5:
                self.dialogue_area.yview("scroll", 1, "units")
        return "break"

    def process_queue(self):
        while not self.message_queue.empty():
            method, args, kwargs = self.message_queue.get()
            method(*args, **kwargs)
        self.root.after(100, self.process_queue)

    def safe_call(self, method, *args, **kwargs):
        self.message_queue.put((method, args, kwargs))

    def toggle_voice(self):
        status = "включен" if self.voice_enabled.get() else "выключен"
        self.update_status(f"Голосовой ответ {status}")

    def send_text(self, event=None):
        if self.is_processing:
            self.update_status("Система занята, подождите...")
            return

        text = self.text_input.get().strip()
        if text:
            self.text_input.delete(0, "end")
            self.is_processing = True
            threading.Thread(target=self.process_input, args=(text,), daemon=True).start()

    def toggle_listening(self):
        if self.is_processing:
            self.update_status("Дождитесь завершения текущей задачи")
            return

        if not self.is_listening:
            self.is_listening = True
            self.is_processing = True
            self.btn_listen.configure(text="Стоп записи", state="disabled")
            self.update_status("Слушаю...")
            threading.Thread(target=self.voice_input, daemon=True).start()
        else:
            self.is_listening = False
            self.btn_listen.configure(text="Старт записи", state="normal")
            self.update_status("Запись остановлена")

    def voice_input(self):
        with sr.Microphone() as source:
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self.safe_call(self.update_status, "Говорите сейчас...")

                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

                text = self.recognizer.recognize_google(audio, language="ru-RU")
                self.safe_call(self.process_input, text.lower())

            except sr.WaitTimeoutError:
                self.safe_call(self.update_status, "Таймаут: речь не обнаружена")
            except sr.UnknownValueError:
                self.safe_call(self.update_status, "Речь не распознана")
            except sr.RequestError as e:
                self.safe_call(self.update_status, f"Ошибка сервиса: {str(e)}")
            except Exception as e:
                self.safe_call(self.update_dialogue, f"Ошибка при распознавании: {str(e)}", "error")
            finally:
                self.safe_call(self.finish_processing)

    def process_input(self, text):
        self.update_dialogue(f"[User]: {text}", "user")

        if text == '?exit':
            self.on_close()
            return

        try:
            response = self.conversation.get_response(text)
            self.update_dialogue(f"[Lumi]: {response}", "assistant")

            if self.voice_enabled.get():
                self.speech.speak(response)
                time.sleep(0.5)  # Пауза для завершения воспроизведения

        except Exception as e:
            self.update_dialogue(f"Ошибка обработки: {str(e)}", "error")
        finally:
            self.finish_processing()

    def finish_processing(self):
        self.is_processing = False
        self.is_listening = False
        self.safe_call(self.btn_listen.configure, text="Старт записи", state="normal")
        self.safe_call(self.update_status, "Готов к работе")

    def update_dialogue(self, text, tag=None):
        if not self.dialogue_area.winfo_exists():
            return

        self.dialogue_area.configure(state="normal")
        self.dialogue_area.insert("end", f"{text}\n", tag)
        self.dialogue_area.configure(state="disabled")
        self.dialogue_area.see("end")

    def update_status(self, message):
        if self.status_bar.winfo_exists():
            self.status_bar.configure(text=message)

    def on_close(self):
        self.speech.stop()
        self.is_listening = False
        self.is_processing = False
        time.sleep(0.5)
        self.root.destroy()


if __name__ == "__main__":
    root = ctk.CTk()
    app = VoiceAssistantApp(root)
    root.mainloop()
