# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt from the root directory of the project to the container's /app directory
COPY /requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy everything from the 'app' directory (where the Dockerfile is) into the container's /app directory
COPY ./app /app

# Make port 8443 available to the world outside this container (optional)
EXPOSE 8443

# Run bot.py when the container launches
CMD ["python", "bot.py"]
