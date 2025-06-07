from g4f.client import Client


class Conversation:
    def __init__(self):
        self.client = Client()
        self.history = [{"role": "system", "content": "You are a helpful assistant."}]

    def add_message(self, role, content):
        self.history.append({"role": role, "content": content})

    def get_response(self, user_message):
        self.add_message("user", user_message)

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.history,
            web_search=True
        )

        assistant_response = response.choices[0].message.content
        self.add_message("assistant", assistant_response)
        return assistant_response