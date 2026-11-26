"""Set isolated settings before test modules import the application."""

import os

os.environ.update({
    "DATABASE_URL": "sqlite://",
    "ENVIRONMENT": "test",
    "JWT_SECRET_KEY": "isolated-test-signing-key-for-synthetic-sessions",
    "GOOGLE_CLIENT_ID": "test-google-client",
    "GOOGLE_CLIENT_SECRET": "test-google-secret",
    "GOOGLE_REDIRECT_URI": "http://localhost:8000/api/integrations/google/callback",
    "AI_PROVIDER": "disabled",
    "CONTEXT_MODEL_PATH": "",
    "CONTEXT_MODEL_REVISION": "",
    "OPENROUTER_API_KEY": "",
    "EMAIL_PROVIDER": "console",
    "INTEGRATION_TOKEN_KEY": "",
    "LANGSMITH_TRACING": "false",
    "LANGCHAIN_TRACING_V2": "false",
})
