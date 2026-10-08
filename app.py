import os
import json
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from tools.calculator import calculate_attendance
from tools.attendance import mark_attendance
from tools.timetable import find_day_timetable

from tools.document_parser.pdf_parser import extract_pdf_text
from tools.document_parser.docx_parser import extract_docx_text
from tools.document_parser.txt_parser import extract_txt_text


# =========================================================
# SETUP
# =========================================================

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=api_key) if api_key else None

st.set_page_config(
    page_title="College AI Assistant",
    page_icon="🎓",
    layout="wide"
)


# =========================================================
# SESSION STATE
# =========================================================

if "document_text" not in st.session_state:
    st.session_state.document_text = ""

if "document_name" not in st.session_state:
    st.session_state.document_name = ""


# =========================================================
# HEADER
# =========================================================

st.title("🎓 College AI Assistant")

st.write(
    "AI-powered assistant for attendance, timetable and college documents."
)

st.divider()


# =========================================================
# FEATURES
# =========================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.info("🧮 Calculator\n\nAttendance percentage")

with col2:
    st.info("📝 Attendance\n\nMark attendance")

with col3:
    st.info("📅 Timetable\n\nFind your classes")


st.divider()


# =========================================================
# MANUAL ATTENDANCE CALCULATOR
# =========================================================

st.subheader("🧮 Attendance Calculator")

with st.form("attendance_calculator"):
    attended = st.number_input(
        "Classes attended",
        min_value=0,
        step=1,
        value=0
    )
    total = st.number_input(
        "Total classes",
        min_value=1,
        step=1,
        value=1
    )

    submitted = st.form_submit_button("Calculate Attendance")

    if submitted:
        try:
            result = calculate_attendance(attended, total)
            st.success(
                f"✅ Attendance percentage: {result}%"
            )
        except ValueError as error:
            st.error(f"❌ {error}")


st.divider()


# =========================================================
# MANUAL ATTENDANCE MARKER
# =========================================================

st.subheader("📝 Mark Attendance")

with st.form("attendance_marker"):
    student_name = st.text_input(
        "Student name",
        value="Rishabh Kumar"
    )
    subject = st.text_input("Subject")
    attendance_date = st.date_input(
        "Date",
        value=datetime.now().date()
    )
    attendance_status = st.selectbox(
        "Status",
        options=["Present", "Absent"]
    )

    attendance_submitted = st.form_submit_button("Save Attendance")

    if attendance_submitted:
        try:
            record = mark_attendance(
                student_name,
                subject,
                attendance_date.strftime("%Y-%m-%d"),
                attendance_status
            )
            st.success("✅ Attendance saved successfully.")
            st.json(record)
        except ValueError as error:
            st.error(f"❌ {error}")


st.divider()


# =========================================================
# DOCUMENT UPLOAD
# =========================================================

st.subheader("📄 Upload College Document")

uploaded_file = st.file_uploader(
    "Upload PDF, DOCX or TXT",
    type=["pdf", "docx", "txt"]
)


if uploaded_file is not None:

    try:

        file_name = uploaded_file.name

        # -----------------------------------------------
        # PDF
        # -----------------------------------------------

        if file_name.lower().endswith(".pdf"):

            with open("uploaded_document.pdf", "wb") as file:

                file.write(
                    uploaded_file.getbuffer()
                )

            document_text = extract_pdf_text(
                "uploaded_document.pdf"
            )


        # -----------------------------------------------
        # DOCX
        # -----------------------------------------------

        elif file_name.lower().endswith(".docx"):

            with open("uploaded_document.docx", "wb") as file:

                file.write(
                    uploaded_file.getbuffer()
                )

            document_text = extract_docx_text(
                "uploaded_document.docx"
            )


        # -----------------------------------------------
        # TXT
        # -----------------------------------------------

        elif file_name.lower().endswith(".txt"):

            with open("uploaded_document.txt", "wb") as file:

                file.write(
                    uploaded_file.getbuffer()
                )

            document_text = extract_txt_text(
                "uploaded_document.txt"
            )


        else:

            document_text = ""


        st.session_state.document_text = document_text
        st.session_state.document_name = file_name

        if document_text.strip():

            st.success(
                f"✅ {file_name} uploaded successfully."
            )

        else:

            st.warning(
                "⚠️ No readable text found in the file."
            )


    except Exception as error:

        st.error(
            f"❌ File error: {error}"
        )


# =========================================================
# AUTOMATIC TEST TIMETABLE
# =========================================================
# If no document was uploaded, automatically load
# test_timetable.txt from the project folder.

if not st.session_state.document_text.strip():

    test_timetable = "test_timetable.txt"

    if os.path.exists(test_timetable):

        try:

            test_text = extract_txt_text(
                test_timetable
            )

            if test_text.strip():

                st.session_state.document_text = test_text
                st.session_state.document_name = test_timetable

                st.info(
                    "📅 Test timetable loaded automatically."
                )

        except Exception as error:

            st.warning(
                f"Could not load test timetable: {error}"
            )


# =========================================================
# SHOW DOCUMENT
# =========================================================

if st.session_state.document_text:

    st.success(
        f"📄 Active document: {st.session_state.document_name}"
    )

    with st.expander("View Extracted Text"):

        st.text(
            st.session_state.document_text
        )


st.divider()


# =========================================================
# QUESTION
# =========================================================

st.subheader("💬 Ask Your Assistant")

question = st.text_input(
    "Enter your question",
    placeholder="Example: What classes do I have on Monday?"
)


# =========================================================
# ASK BUTTON
# =========================================================

if not api_key:
    st.warning(
        "⚠️ OPENAI_API_KEY is missing. Add it to your .env file to enable AI-powered answers. The calculator and attendance tools still work manually above."
    )

else:
    if st.button(
        "🤖 Ask AI",
        type="primary"
    ):

        if not question.strip():
            st.warning("Please enter a question.")
            st.stop()

        today = datetime.now().strftime("%Y-%m-%d")
        document_text = st.session_state.document_text

        days = {
            "monday": "Monday",
            "tuesday": "Tuesday",
            "wednesday": "Wednesday",
            "thursday": "Thursday",
            "friday": "Friday",
            "saturday": "Saturday",
            "sunday": "Sunday"
        }

        question_lower = question.lower()
        detected_day = None

        for key, value in days.items():
            if key in question_lower:
                detected_day = value
                break

        if detected_day is not None:
            if not document_text.strip():
                st.warning("⚠️ Timetable data is not available.")
                st.stop()

            timetable_result = find_day_timetable(document_text, detected_day)

            st.success("🤖 AI Response")

            if timetable_result:
                st.subheader(f"📅 Classes on {detected_day}")
                for item in timetable_result:
                    st.write(f"• {item}")
            else:
                st.warning(f"No timetable entries were found for {detected_day}.")

            st.caption("🔧 Tool Used: Timetable Tool")
            st.stop()

        tools = [
            {
                "type": "function",
                "name": "calculate_attendance",
                "description": "Calculate attendance percentage.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "attended": {"type": "integer"},
                        "total": {"type": "integer"}
                    },
                    "required": ["attended", "total"]
                }
            },
            {
                "type": "function",
                "name": "mark_attendance",
                "description": "Mark student attendance.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "status": {"type": "string", "enum": ["Present", "Absent"]}
                    },
                    "required": ["subject", "status"]
                }
            }
        ]

        instructions = f"""
You are College AI Assistant.

Student name:
Rishabh Kumar

Today's date:
{today}

Use the Calculator Tool for attendance percentage.

Use the Attendance Tool when the student wants to mark attendance.

Never invent information.

Always mention the tool used.
"""

        try:
            response = client.responses.create(
                model=MODEL_NAME,
                instructions=instructions,
                input=question,
                tools=tools
            )

            tool_outputs = []
            tools_used = []

            for item in response.output:
                if item.type != "function_call":
                    continue

                arguments = json.loads(item.arguments)

                if item.name == "calculate_attendance":
                    result = calculate_attendance(arguments["attended"], arguments["total"])
                    tools_used.append("Calculator Tool")
                    tool_outputs.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps({"percentage": result})
                    })

                elif item.name == "mark_attendance":
                    result = mark_attendance(
                        "Rishabh Kumar",
                        arguments["subject"],
                        today,
                        arguments["status"]
                    )
                    tools_used.append("Attendance Tool")
                    tool_outputs.append({
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result)
                    })

            if tool_outputs:
                final_response = client.responses.create(
                    model=MODEL_NAME,
                    instructions="""
Give the student a clear final answer.

Do not invent information.

Mention which tool was used.
""",
                    input=[*response.output, *tool_outputs],
                    tools=tools
                )

                st.success("🤖 AI Response")
                st.write(final_response.output_text)
                st.caption("🔧 Tool Used: " + ", ".join(tools_used))
            else:
                st.success("🤖 AI Response")
                st.write(response.output_text)

        except Exception as error:
            st.error(f"❌ AI Error: {error}")