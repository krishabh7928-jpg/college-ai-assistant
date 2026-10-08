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


# -------------------------------------------------
# CONFIGURATION
# -------------------------------------------------

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


st.set_page_config(
    page_title="College AI Assistant",
    page_icon="🎓"
)


# -------------------------------------------------
# SESSION STATE
# -------------------------------------------------

if "document_text" not in st.session_state:
    st.session_state.document_text = ""

if "document_name" not in st.session_state:
    st.session_state.document_name = ""


# -------------------------------------------------
# HEADER
# -------------------------------------------------

st.title("🎓 College AI Assistant")

st.write(
    "Your smart college assistant powered by AI and custom tools."
)


# -------------------------------------------------
# DOCUMENT UPLOAD
# -------------------------------------------------

st.subheader("📄 Upload College Document")

uploaded_file = st.file_uploader(
    "Upload PDF, DOCX or TXT",
    type=["pdf", "docx", "txt"]
)


if uploaded_file:

    file_name = uploaded_file.name

    try:

        # -----------------------------
        # PDF
        # -----------------------------

        if file_name.lower().endswith(".pdf"):

            with open(
                "uploaded_document.pdf",
                "wb"
            ) as file:

                file.write(
                    uploaded_file.getbuffer()
                )

            extracted_text = extract_pdf_text(
                "uploaded_document.pdf"
            )


        # -----------------------------
        # DOCX
        # -----------------------------

        elif file_name.lower().endswith(".docx"):

            with open(
                "uploaded_document.docx",
                "wb"
            ) as file:

                file.write(
                    uploaded_file.getbuffer()
                )

            extracted_text = extract_docx_text(
                "uploaded_document.docx"
            )


        # -----------------------------
        # TXT
        # -----------------------------

        elif file_name.lower().endswith(".txt"):

            with open(
                "uploaded_document.txt",
                "wb"
            ) as file:

                file.write(
                    uploaded_file.getbuffer()
                )

            extracted_text = extract_txt_text(
                "uploaded_document.txt"
            )


        # -----------------------------
        # SAVE IN SESSION
        # -----------------------------

        st.session_state.document_text = extracted_text

        st.session_state.document_name = file_name


        st.success(
            f"✅ {file_name} uploaded successfully!"
        )


    except Exception as error:

        st.error(
            f"Error reading document: {error}"
        )


# -------------------------------------------------
# SHOW UPLOADED DOCUMENT
# -------------------------------------------------

if st.session_state.document_text:

    with st.expander(
        "📖 View Extracted Text"
    ):

        st.text(
            st.session_state.document_text
        )


st.divider()


# -------------------------------------------------
# AI CHAT
# -------------------------------------------------

st.subheader("💬 Ask Your College Assistant")


question = st.text_input(
    "Enter your question:",
    placeholder="Example: My attendance is 35 out of 42 classes"
)


# -------------------------------------------------
# ASK AI
# -------------------------------------------------

if st.button("Ask AI"):

    if not question:

        st.warning(
            "Please enter a question."
        )

    else:

        today = datetime.now().strftime(
            "%Y-%m-%d"
        )


        # Get document from session
        document_text = st.session_state.document_text


        # -------------------------------------------------
        # TOOL DEFINITIONS
        # -------------------------------------------------

        tools = [

            # -------------------------------------------------
            # CALCULATOR TOOL
            # -------------------------------------------------

            {
                "type": "function",
                "name": "calculate_attendance",

                "description":
                    "Calculate attendance percentage using attended classes and total classes.",

                "parameters": {

                    "type": "object",

                    "properties": {

                        "attended": {
                            "type": "integer",
                            "description":
                                "Number of classes attended"
                        },

                        "total": {
                            "type": "integer",
                            "description":
                                "Total number of classes"
                        }
                    },

                    "required": [
                        "attended",
                        "total"
                    ]
                }
            },


            # -------------------------------------------------
            # ATTENDANCE TOOL
            # -------------------------------------------------

            {
                "type": "function",
                "name": "mark_attendance",

                "description":
                    "Mark student attendance for a particular subject and date.",

                "parameters": {

                    "type": "object",

                    "properties": {

                        "student_name": {
                            "type": "string",
                            "description":
                                "Student name"
                        },

                        "subject": {
                            "type": "string",
                            "description":
                                "Subject name"
                        },

                        "date": {
                            "type": "string",
                            "description":
                                "Date in YYYY-MM-DD format"
                        },

                        "status": {
                            "type": "string",
                            "enum": [
                                "Present",
                                "Absent"
                            ],
                            "description":
                                "Attendance status"
                        }
                    },

                    "required": [
                        "student_name",
                        "subject",
                        "date",
                        "status"
                    ]
                }
            },


            # -------------------------------------------------
            # TIMETABLE TOOL
            # -------------------------------------------------

            {
                "type": "function",
                "name": "find_day_timetable",

                "description":
                    "Find timetable information for a particular day from the uploaded college timetable.",

                "parameters": {

                    "type": "object",

                    "properties": {

                        "day": {
                            "type": "string",
                            "description":
                                "Day of the week such as Monday, Tuesday, Wednesday, Thursday or Friday"
                        }
                    },

                    "required": [
                        "day"
                    ]
                }
            }

        ]


        # -------------------------------------------------
        # AI INSTRUCTIONS
        # -------------------------------------------------

        instructions = f"""
You are a College AI Assistant.

Student name:
Rishabh Kumar

Today's date:
{today}

Available tools:

1. Calculator Tool
Use it for attendance percentage calculations.

2. Attendance Tool
Use it when the student wants to mark attendance.

3. Timetable Tool
Use it when the student asks about their timetable
or classes on a particular day.

Important rules:

- Always use Rishabh Kumar as the student name.
- If the student says today, use {today}.
- Never invent a different date.
- Use Present or Absent according to the request.
- Use the appropriate tool when required.
- After using a tool, provide a natural-language final answer.
- Always mention the tool used.

Uploaded document:

{document_text}
"""


        # -------------------------------------------------
        # FIRST LLM CALL
        # -------------------------------------------------

        response = client.responses.create(

            model="gpt-6-luna",

            instructions=instructions,

            input=question,

            tools=tools
        )


        # -------------------------------------------------
        # TOOL PROCESSING
        # -------------------------------------------------

        tool_outputs = []

        tools_used = []


        for item in response.output:

            if item.type != "function_call":
                continue


            arguments = json.loads(
                item.arguments
            )


            # -------------------------------------------------
            # CALCULATOR
            # -------------------------------------------------

            if item.name == "calculate_attendance":

                result = calculate_attendance(

                    arguments["attended"],

                    arguments["total"]
                )


                tools_used.append(
                    "Calculator"
                )


                tool_outputs.append({

                    "type":
                        "function_call_output",

                    "call_id":
                        item.call_id,

                    "output":
                        json.dumps({

                            "attendance_percentage":
                                result

                        })
                })


            # -------------------------------------------------
            # ATTENDANCE
            # -------------------------------------------------

            elif item.name == "mark_attendance":

                result = mark_attendance(

                    "Rishabh Kumar",

                    arguments["subject"],

                    today,

                    arguments["status"]
                )


                tools_used.append(
                    "Attendance Tool"
                )


                tool_outputs.append({

                    "type":
                        "function_call_output",

                    "call_id":
                        item.call_id,

                    "output":
                        json.dumps(result)
                })


            # -------------------------------------------------
            # TIMETABLE
            # -------------------------------------------------

            elif item.name == "find_day_timetable":

                day = arguments["day"]


                if document_text:

                    result = find_day_timetable(

                        document_text,

                        day
                    )

                else:

                    result = []


                tools_used.append(
                    "Timetable Tool"
                )


                tool_outputs.append({

                    "type":
                        "function_call_output",

                    "call_id":
                        item.call_id,

                    "output":
                        json.dumps({

                            "day":
                                day,

                            "timetable":
                                result

                        })
                })


        # -------------------------------------------------
        # FINAL LLM RESPONSE
        # -------------------------------------------------

        if tool_outputs:

            final_response = client.responses.create(

                model="gpt-6-luna",

                instructions=f"""
Give the student a clear final answer.

Student:
Rishabh Kumar

Today's date:
{today}

Explain the tool result accurately.

Do not invent information.

Always mention the tool used.
""",

                input=[
                    *response.output,
                    *tool_outputs
                ],

                tools=tools
            )


            st.success(
                "🤖 AI Response"
            )


            st.write(
                final_response.output_text
            )


            st.info(
                "🔧 Tool Used: "
                + ", ".join(tools_used)
            )


        else:

            st.success(
                "🤖 AI Response"
            )

            st.write(
                response.output_text
            )
            
            
                
            