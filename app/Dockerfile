# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install sqlite3 and any required build dependencies
RUN apt-get update && \
    apt-get install -y sqlite3 libsqlite3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements.txt from the root directory of the project to the container's /app directory
COPY /requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

RUN mkdir -p /app/sessions

# Copy everything from the 'app' directory (where the Dockerfile is) into the container's /app directory
COPY ./app /app

# Make port 8443 available to the world outside this container (optional)
EXPOSE 8443

# Run bot.py when the container launches
CMD ["python", "bot_pyro.py"]
