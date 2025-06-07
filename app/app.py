import customtkinter as ctk
import tkinter as tk
import threading
import speech_recognition as sr
from module.conversation import Conversation
from module.speech_synthesizer import SpeechSynthesizer
import os


class VoiceAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Голосовой ассистент")
        self.root.geometry("600x350")
        self.root.resizable(False, False)

        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))

        theme_path = os.path.join(self.BASE_DIR, "theme", "app_theme.json")
        ctk.set_default_color_theme(theme_path)

        self.conversation = Conversation()
        self.recognizer = sr.Recognizer()
        self.is_listening = False
        self.voice_enabled = ctk.BooleanVar(value=True)
        self.speech = SpeechSynthesizer(self.update_status)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme(os.path.join(self.BASE_DIR, "./theme/app_theme.json"))

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_widgets()
        self.create_context_menu()

    def create_widgets(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(4, weight=1)

        control_frame = ctk.CTkFrame(self.root)
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

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
        input_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.text_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Введите сообщение..."
        )

        self.text_input._entry.configure(
            selectbackground="#638C6D",
            selectforeground="white"
        )

        self.text_input.pack(side="left", fill="x", expand=True, padx=5)
        self.text_input.bind("<Return>", lambda event: self.send_text())
        self.text_input._entry.bind("<Button-3>", self.show_context_menu)
        self.text_input._entry.bind("<Control-v>", self.paste_text)
        self.text_input._entry.bind("<Control-V>", self.paste_text)
        self.text_input._entry.bind("<Control-x>", self.cut_text)
        self.text_input._entry.bind("<Control-X>", self.cut_text)
        self.text_input._entry.bind("<Control-c>", self.copy_text)
        self.text_input._entry.bind("<Control-C>", self.copy_text)

        self.btn_send = ctk.CTkButton(
            input_frame,
            text="Отправить",
            command=self.send_text
        )
        self.btn_send.pack(side="left", padx=5)

        self.dialogue_area = ctk.CTkTextbox(
            self.root,
            wrap="word",
            font=("Arial", 12),
            activate_scrollbars=True,
            state="disabled"
        )
        self.dialogue_area.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")

        text_widget = self.dialogue_area._textbox
        text_widget.configure(
            exportselection=1,
            selectbackground="#638C6D",
            inactiveselectbackground="#638C6D"
        )

        text_widget.bind("<Control-c>", self.copy_text)
        text_widget.bind("<Button-3>", self.show_context_menu)

        self.status_bar = ctk.CTkLabel(
            self.root,
            text="Готов к работе",
            anchor="w",
            corner_radius=0
        )
        self.status_bar.grid(row=3, column=0, sticky="ew", padx=10)

    def create_context_menu(self):
        self.context_menu = tk.Menu(self.root,
                                    tearoff=0,
                                    activebackground="#629618"
                                    )
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
        self.context_menu.entryconfig("Вырезать", state="normal")
        self.context_menu.entryconfig("Копировать", state="normal")
        self.context_menu.entryconfig("Вставить", state="normal")

        if event.widget == self.dialogue_area._textbox:
            if not event.widget.tag_ranges("sel"):
                self.context_menu.entryconfig("Вырезать", state="disabled")
                self.context_menu.entryconfig("Копировать", state="disabled")
        elif event.widget == self.text_input._entry:
            if not event.widget.selection_present():
                self.context_menu.entryconfig("Вырезать", state="disabled")
                self.context_menu.entryconfig("Копировать", state="disabled")

        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def cut_text(self, event=None):
        widget = self.root.focus_get()
        if widget == self.dialogue_area._textbox:
            self.copy_text()
            widget.delete("sel.first", "sel.last")
        elif widget == self.text_input._entry:
            self.copy_text()
            widget.delete(tk.SEL_FIRST, tk.SEL_LAST)

    def copy_text(self, event=None):
        widget = self.root.focus_get()
        if widget == self.dialogue_area._textbox and widget.tag_ranges("sel"):
            selected_text = widget.get("sel.first", "sel.last")
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        elif widget == self.text_input._entry and widget.selection_present():
            selected_text = widget.get()
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text[widget.index(tk.SEL_FIRST):widget.index(tk.SEL_LAST)])

    def paste_text(self, event=None):
        widget = self.root.focus_get()
        if widget == self.dialogue_area._textbox:
            widget.insert(tk.INSERT, self.root.clipboard_get())
        elif widget == self.text_input._entry:
            widget.insert(tk.INSERT, self.root.clipboard_get())

    def on_close(self):
        self.speech.stop()
        self.root.destroy()

    def toggle_voice(self):
        status = "включен" if self.voice_enabled.get() else "выключен"
        self.update_status(f"Голосовой ответ {status}")

    def send_text(self):
        text = self.text_input.get()
        if text.strip():
            self.text_input.delete(0, "end")
            self.process_input(text)

    def toggle_listening(self):
        if not self.is_listening:
            self.is_listening = True
            self.btn_listen.configure(text="Стоп записи")
            self.update_status("Слушаю...")
            threading.Thread(target=self.voice_input).start()
        else:
            self.is_listening = False
            self.btn_listen.configure(text="Старт записи")
            self.update_status("Готов к работе")
            self.speech.stop()

    def voice_input(self):
        with sr.Microphone() as source:
            try:
                audio = self.recognizer.listen(source, timeout=5)
                text = self.recognizer.recognize_google(audio, language="ru-RU")
                self.process_input(text.lower())
            except sr.UnknownValueError:
                self.update_status("Речь не распознана")
            except Exception as e:
                self.update_status(f"Ошибка: {str(e)}")

        self.is_listening = False
        self.btn_listen.after(0, lambda: self.btn_listen.configure(text="Старт записи"))

    def process_input(self, text):
        self.update_dialogue(f"Вы: {text}", "user")

        if text == 'выход':
            self.on_close()
            return

        threading.Thread(target=self.get_bot_response, args=(text,)).start()

    def get_bot_response(self, text):
        response = self.conversation.get_response(text)
        self.update_dialogue(f"Ассистент: {response}", "assistant")
        if self.voice_enabled.get():
            self.speech.speak(response)

    def update_dialogue(self, text, role):
        self.dialogue_area.configure(state="normal")
        self.dialogue_area.insert("end", f"\n{text}\n")
        self.dialogue_area.configure(state="disabled")
        self.dialogue_area.see("end")

    def update_status(self, message):
        self.status_bar.configure(text=message)


if __name__ == "__main__":
    root = ctk.CTk()
    app = VoiceAssistantApp(root)
    root.mainloop()
