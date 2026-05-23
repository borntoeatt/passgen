# Slim Python image — small, regularly patched.
FROM python:3.12-slim

WORKDIR /app

# Install runtime deps first (cached layer when only source changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Flask app (passgen/ holds app.py, password_generator.py, templates/).
COPY passgen/ ./passgen/

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Drop privileges. nobody (uid 65534) is present in python:slim and has no shell.
USER nobody

# gunicorn ignores `if __name__ == '__main__'` so the app's debug=True is bypassed.
# --chdir passgen so the `from password_generator import ...` import in app.py resolves.
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--chdir", "passgen", "--workers", "2", "--access-logfile", "-", "app:app"]
