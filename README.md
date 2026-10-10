# College AI Assistant

This project runs as a FastAPI web app so it can be deployed to Vercel.

## Run locally

Install dependencies, then start the app:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Open `http://localhost:8000`. For AI answers locally, set `OPENAI_API_KEY` in
the ignored `.env` file. `OPENAI_MODEL` is optional and defaults to
`gpt-4o-mini`.

## Deploy to Vercel

1. Import this GitHub repository in Vercel and keep the project root set to the
   repository root. Vercel detects the FastAPI `app` in `app.py`.
2. In **Project Settings → Environment Variables**, add `OPENAI_API_KEY` with
   your API key. Optionally add `OPENAI_MODEL`.
3. Enable the environment(s) you use, save the variables, and redeploy.

Never commit `.env` or paste an API key into source code. Vercel environment
variables are available only to the server-side Python app.

Document uploads accept PDF, DOCX, or TXT files up to 4 MB. Attendance records
are returned when submitted, but are not durable on Vercel because serverless
instances do not provide persistent storage. Add a database if records must be
retained across requests or users.
