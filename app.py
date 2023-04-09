import openai
import streamlit as st
from streamlit_chat import message
import json
from datetime import datetime

st.set_page_config(page_title="Tutor Chat", page_icon=":robot_face:")

def load_syllabus(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def save_syllabus(data, file_path):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


def display_syllabus(syllabus_data):
    st.subheader(f"Student Name: {syllabus_data['student_name']}")

    chapter_titles = [chapter["title"] for chapter in syllabus_data["chapters"]]
    selected_chapter_title = st.sidebar.selectbox("Select a chapter:", chapter_titles)
    selected_chapter = next(chapter for chapter in syllabus_data["chapters"] if chapter["title"] == selected_chapter_title)

    st.subheader(selected_chapter["title"])

    for sub_lesson in selected_chapter["sub_lessons"]:
        completed = st.checkbox(sub_lesson["title"], value=sub_lesson["completed"])
        if completed != sub_lesson["completed"]:
            sub_lesson["completed"] = completed
            sub_lesson["completion_time"] = None if not completed else datetime.now().isoformat()
            save_syllabus(syllabus_data, syllabus_file)

        st.markdown(sub_lesson["content"])


def display_profile(syllabus_data):
    st.header("User Profile")

    new_student_name = st.text_input("Update your name:", value=syllabus_data["student_name"])
    if new_student_name != syllabus_data["student_name"]:
        syllabus_data["student_name"] = new_student_name
        save_syllabus(syllabus_data, syllabus_file)

    if st.button("Reset Syllabus"):
        for chapter in syllabus_data["chapters"]:
            chapter["completed"] = False
            chapter["completion_time"] = None
            for sub_lesson in chapter["sub_lessons"]:
                sub_lesson["completed"] = False
                sub_lesson["completion_time"] = None
        save_syllabus(syllabus_data, syllabus_file)

    total_sub_lessons = sum([len(chapter["sub_lessons"]) for chapter in syllabus_data["chapters"]])
    completed_sub_lessons = sum([sum([sub_lesson["completed"] for sub_lesson in chapter["sub_lessons"]]) for chapter in syllabus_data["chapters"]])
    progress = int((completed_sub_lessons / total_sub_lessons) * 100)

    st.progress(progress)
    st.write(f"Progress: {progress}% completed")


def display_side_bar():
    # Sidebar - let user choose model, show total cost of current conversation, and let user clear the current conversation
    st.sidebar.title("Sidebar")
    model_name = st.sidebar.radio("Choose a model:", ("GPT-3.5", "GPT-4"))
    counter_placeholder = st.sidebar.empty()
    counter_placeholder.write(f"Total cost of this conversation: ${st.session_state['total_cost']:.5f}")
    clear_button = st.sidebar.button("Clear Conversation", key="clear")

    # Map model names to OpenAI model IDs
    if model_name == "GPT-3.5":
        model = "gpt-3.5-turbo"
    else:
        model = "gpt-4"

    # reset everything
    if clear_button:
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
        counter_placeholder.write(f"Total cost of this conversation: ${st.session_state['total_cost']:.5f}")

    return model_name, model, counter_placeholder


def init_session_info():
    # Set org ID and API key
    openai.organization = "<YOUR_OPENAI_ORG_ID>"
    openai.api_key = "<YOUR_OPENAI_API_KEY>"

    # Initialise session state variables
    if 'generated' not in st.session_state:
        st.session_state['generated'] = []
    if 'past' not in st.session_state:
        st.session_state['past'] = []
    if 'messages' not in st.session_state:
        st.session_state['messages'] = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
    if 'model_name' not in st.session_state:
        st.session_state['model_name'] = []
    if 'cost' not in st.session_state:
        st.session_state['cost'] = []
    if 'total_tokens' not in st.session_state:
        st.session_state['total_tokens'] = []
    if 'total_cost' not in st.session_state:
        st.session_state['total_cost'] = 0.0

def display_chat_box(model_name, model, counter_placeholder):
    # container for chat history
    response_container = st.container()
    # container for text box
    container = st.container()

    with container:
        with st.form(key='my_form', clear_on_submit=True):
            user_input = st.text_area("You:", key='input', height=100)
            submit_button = st.form_submit_button(label='Send')

        if submit_button and user_input:
            output, total_tokens, prompt_tokens, completion_tokens = generate_response(user_input, model)
            st.session_state['past'].append(user_input)
            st.session_state['generated'].append(output)
            st.session_state['model_name'].append(model_name)
            st.session_state['total_tokens'].append(total_tokens)

            # from https://openai.com/pricing#language-models
            if model_name == "GPT-3.5":
                cost = total_tokens * 0.002 / 1000
            else:
                cost = (prompt_tokens * 0.03 + completion_tokens * 0.06) / 1000

            st.session_state['cost'].append(cost)
            st.session_state['total_cost'] += cost

    if st.session_state['generated']:
        with response_container:
            for i in range(len(st.session_state['generated'])):
                message(st.session_state["past"][i], is_user=True, key=str(i) + '_user')
                message(st.session_state["generated"][i], key=str(i))
                st.write(
                    f"Model used: {st.session_state['model_name'][i]}; Number of tokens: {st.session_state['total_tokens'][i]}; Cost: ${st.session_state['cost'][i]:.5f}")
                counter_placeholder.write(f"Total cost of this conversation: ${st.session_state['total_cost']:.5f}")

# generate a response
def generate_response(prompt, model):
    st.session_state['messages'].append({"role": "user", "content": prompt})

    completion = openai.ChatCompletion.create(
        model=model,
        messages=st.session_state['messages']
    )
    response = completion.choices[0].message.content
    st.session_state['messages'].append({"role": "assistant", "content": response})

    # print(st.session_state['messages'])
    total_tokens = completion.usage.total_tokens
    prompt_tokens = completion.usage.prompt_tokens
    completion_tokens = completion.usage.completion_tokens
    return response, total_tokens, prompt_tokens, completion_tokens




init_session_info()

# Load the syllabus JSON data
syllabus_file = "syllabus.json"
syllabus_data = load_syllabus(syllabus_file)

st.title("Python Coding Syllabus")

model_name, model, counter_placeholder = display_side_bar()

tab = st.sidebar.radio("Select a tab:", ["Syllabus", "Profile"])

if tab == "Syllabus":
    display_syllabus(syllabus_data)
    display_chat_box(model_name, model, counter_placeholder)
elif tab == "Profile":
    display_profile(syllabus_data)





# Setting page title and header

# st.markdown("<h1 style='text-align: center;'>Python Tutor Bot </h1>", unsafe_allow_html=True)


