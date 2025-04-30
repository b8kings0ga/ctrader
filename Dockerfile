# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install uv
RUN pip install uv

# Copy the project files into the container
COPY pyproject.toml uv.lock ./
COPY README.md ./
COPY src ./src
COPY config ./config

# Install dependencies using uv
# Using --system to install into the global site-packages, as we are in a container
RUN uv sync

# Make port 8000 available to the world outside this container (if needed for future API)
# EXPOSE 8000

# Define environment variables (if needed)
# ENV NAME World

# Run the application using the CLI entry point
# Default command uses default strategy and symbol from config
ENTRYPOINT ["/app/.venv/bin/python", "src/cli/main.py"]
CMD ["run"]