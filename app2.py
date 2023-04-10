import openai
import streamlit as st
from streamlit_chat import message
import json
from datetime import datetime
from key import get_key

st.set_page_config(page_title="Tutor Chat", page_icon=":robot_face:")

SYLLABUS_FILE = "syllabus.json"

class Syllabus:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = self.load()

    def load(self):
        with open(self.file_path, "r") as f:
            return json.load(f)

    def save(self):
        with open(self.file_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def update_student_name(self, new_student_name):
        if new_student_name != self.data["student_name"]:
            self.data["student_name"] = new_student_name
            self.save()

    def update_max_context_size(self, new_max_context_size):
        if new_max_context_size != self.data["max_context_size"]:
            self.data["max_context_size"] = new_max_context_size
            self.save()

    def reset(self):
        for chapter in self.data["chapters"]:
            chapter["conversation_history"] = []
            chapter["completed"] = False
            chapter["completion_time"] = None
            for sub_lesson in chapter["sub_lessons"]:
                sub_lesson["completed"] = False
                sub_lesson["completion_time"] = None
        self.save()

    def get_chapter(self, chapter_title):
        return next(chapter for chapter in self.data["chapters"] if chapter["title"] == chapter_title)

    def update_sub_lesson_completion(self, chapter, sub_lesson_title, completed):
        sub_lesson = next(sub_lesson for sub_lesson in chapter["sub_lessons"] if sub_lesson["title"] == sub_lesson_title)
        if completed != sub_lesson["completed"]:
            sub_lesson["completed"] = completed
            sub_lesson["completion_time"] = None if not completed else datetime.now().isoformat()
            self.save()

    # def append_conversation_history(self, chapter, user_input, output):
    #     chapter["conversation_history"].append(user_input)
    #     chapter["conversation_history"].append(output)
    #     self.save()

    def extend_conversation_history(self, chapter, conversation):
        chapter["conversation_history"].extend(conversation)
        self.save()

class UI:
    def __init__(self, syllabus):
        self.syllabus = syllabus
        self.init_session_info()

    def init_session_info(self):
        openai.organization = ""
        openai.api_key = get_key()

        if "generated" not in st.session_state:
            st.session_state["generated"] = []
        if "past" not in st.session_state:
            st.session_state["past"] = []
        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "system", "content": "You are a helpful assistant."}]
        if "model_name" not in st.session_state:
            st.session_state["model_name"] = []
        if "cost" not in st.session_state:
            st.session_state["cost"] = []
        if "total_tokens" not in st.session_state:
            st.session_state["total_tokens"] = []
        if "total_cost" not in st.session_state:
            st.session_state["total_cost"] = 0.0
        if "selected_chapter" not in st.session_state:
            st.session_state["selected_chapter"] = ""

    def run(self):
        self.init_session_info()

        st.title("Python Coding Syllabus")

        model_name, model, counter_placeholder = self.display_side_bar()

        tab = st.sidebar.radio("Select a tab:", ["Syllabus", "Profile"])

        if tab == "Syllabus":
            self.display_syllabus()
            self.display_chat_box(model_name, model, counter_placeholder)
        elif tab == "Profile":
            self.display_profile()

    # def run(self):
    #     st.title("Python Coding Syllabus")

    #     model_name, model, counter_placeholder = self.display_side_bar()

    #     tab = st.sidebar.radio("Select a tab:", ["Syllabus", "Profile"])

    #     if tab == "Syllabus":
    #         self.display_syllabus()
    #         self.display_chat_box(model_name, model, counter_placeholder)
    #     elif tab == "Profile":
    #         self.display_profile()

    def display_syllabus(self):
        st.subheader(f"Student Name: {self.syllabus.data['student_name']}")

        chapter_titles = [chapter["title"] for chapter in self.syllabus.data["chapters"]]
        selected_chapter_title = st.sidebar.selectbox("Select a chapter:", chapter_titles)
        st.session_state["selected_chapter"] = selected_chapter_title
        selected_chapter = self.syllabus.get_chapter(selected_chapter_title)

        st.subheader(selected_chapter["title"])

        for sub_lesson in selected_chapter["sub_lessons"]:
            completed = st.checkbox(sub_lesson["title"], value=sub_lesson["completed"])
            if completed != sub_lesson["completed"]:
                self.syllabus.update_sub_lesson_completion(selected_chapter, sub_lesson["title"], completed)

            st.markdown(sub_lesson["content"])

    def display_profile(self):
        st.header("User Profile")

        new_student_name = st.text_input("Update your name:", value=self.syllabus.data["student_name"])
        self.syllabus.update_student_name(new_student_name)

        max_context_size = st.text_input("Update Max Context Size:", value=self.syllabus.data["max_context_size"])
        self.syllabus.update_max_context_size(max_context_size)

        if st.button("Reset Syllabus"):
            self.syllabus.reset()

        total_sub_lessons = sum([len(chapter["sub_lessons"]) for chapter in self.syllabus.data["chapters"]])
        completed_sub_lessons = sum([sum([sub_lesson["completed"] for sub_lesson in chapter["sub_lessons"]]) for chapter in self.syllabus.data["chapters"]])
        progress = int((completed_sub_lessons / total_sub_lessons) * 100)

        st.progress(progress)
        st.write(f"Progress: {progress}% completed")

    def display_side_bar(self):
        st.sidebar.title("Sidebar")
        model_name = st.sidebar.radio("Choose a model:", ("GPT-3.5", "GPT-4"))
        counter_placeholder = st.sidebar.empty()
        counter_placeholder.write(f"Total cost of this conversation: ${st.session_state['total_cost']:.5f}")
        clear_button = st.sidebar.button("Clear Conversation", key="clear")

        if model_name == "GPT-3.5":
            model = "gpt-3.5-turbo"
        else:
            model = "gpt-4"

        if clear_button:
            self.reset_conversation()
            counter_placeholder.write(f"Total cost of this conversation: ${st.session_state['total_cost']:.5f}")

        return model_name, model, counter_placeholder

    def reset_conversation(self):
        st.session_state['generated'] = []
        st.session_state['past'] = []
        st.session_state['messages'] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        st.session_state['number_tokens'] = []
        st.session_state['model_name'] = []
        st.session_state['cost'] = []
        st.session_state['total_cost'] = 0.0
        st.session_state['total_tokens'] = []

    def calc_cost(self, model_name, total_tokens, prompt_tokens, completion_tokens):
        if model_name in ["GPT-3.5", "gpt-3.5-turbo"]:
            cost = total_tokens * 0.002 / 1000
        else:
            cost = (prompt_tokens * 0.03 + completion_tokens * 0.06) / 1000
        return cost


    def display_chat_box(self, model_name, model, counter_placeholder):
        response_container = st.container()
        container = st.container()

        with container:
            with st.form(key="my_form", clear_on_submit=True):
                user_input = st.text_area("You:", key="input", height=100)
                submit_button = st.form_submit_button(label="Send")

            selected_chapter_title = st.session_state["selected_chapter"]
            selected_chapter = self.syllabus.get_chapter(selected_chapter_title)
            
            if submit_button and user_input:
                output, total_tokens, prompt_tokens, completion_tokens = self.generate_response(user_input, model, selected_chapter_title)
                st.session_state["past"].append(user_input)
                st.session_state["generated"].append(output)
                st.session_state["model_name"].append(model_name)
                st.session_state["total_tokens"].append(total_tokens)

                if model_name == "GPT-3.5":
                    cost = total_tokens * 0.002 / 1000
                else:
                    cost = (prompt_tokens * 0.03 + completion_tokens * 0.06) / 1000

                cost = self.calc_cost(model_name, total_tokens, prompt_tokens, completion_tokens)

                st.session_state["cost"].append(cost)
                st.session_state["total_cost"] += cost

        if selected_chapter["conversation_history"]:
            with response_container:
                for i in range(len(selected_chapter["conversation_history"])):
                    role = selected_chapter["conversation_history"][i]["role"]                    

                    if role == "info":

                        total_tokens = selected_chapter["conversation_history"][i]["total_tokens"]
                        prompt_tokens = selected_chapter["conversation_history"][i]["prompt_tokens"]
                        completion_tokens = selected_chapter["conversation_history"][i]["completion_tokens"]
                        model = selected_chapter["conversation_history"][i]["model"]
                        cost = self.calc_cost(model, total_tokens, prompt_tokens, completion_tokens)

                        st.write(
                        f"Model used: {model}; Number of tokens: {total_tokens}; Cost: ${cost:.5f}")
                        counter_placeholder.write(f"Total cost of this conversation: ${st.session_state['total_cost']:.5f}")      
                    else:
                        content = selected_chapter["conversation_history"][i]["content"]
                        message(content, is_user=role == "user", key=f"{str(i)}_{role}")
                    
        # if st.session_state["generated"]:
        #     with response_container:
        #         for i in range(len(st.session_state["generated"])):
        #             message(st.session_state["past"][i], is_user=True, key=str(i) + "_user")
        #             message(st.session_state["generated"][i], key=str(i))
        #             st.write(
        #                 f"Model used: {st.session_state['model_name'][i]}; Number of tokens: {st.session_state['total_tokens'][i]}; Cost: ${st.session_state['cost'][i]:.5f}")
        #             counter_placeholder.write(f"Total cost of this conversation: ${st.session_state['total_cost']:.5f}")

    def generate_response(self, prompt, model, selected_chapter_title):
        st.session_state["messages"].append({"role": "user", "content": prompt})

        completion = openai.ChatCompletion.create(
            model=model,
            messages=st.session_state["messages"]
        )
        response = completion.choices[0].message.content
        st.session_state["messages"].append({"role": "assistant", "content": response})

        selected_chapter = self.syllabus.get_chapter(selected_chapter_title)
        self.syllabus.extend_conversation_history(selected_chapter, [{"role": "user", "content": prompt}, {"role": "assistant", "content": response}, {"role": "info","model": model, "total_tokens": completion.usage.total_tokens, "prompt_tokens":completion.usage.prompt_tokens, "completion_tokens":completion.usage.completion_tokens }])

        total_tokens = completion.usage.total_tokens
        prompt_tokens = completion.usage.prompt_tokens
        completion_tokens = completion.usage.completion_tokens
        return response, total_tokens, prompt_tokens, completion_tokens



syllabus = Syllabus(SYLLABUS_FILE)
app = UI(syllabus)
app.run()